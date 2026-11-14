import os, json, sqlite3, base64, re, io
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from PIL import Image, ImageChops, ImageStat
from rules_engine import analyze_brand_content, split_items
from gemini_service import analyze_with_gemini

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'brandguard.db'))


def get_db_connection():
    c = sqlite3.connect(DATABASE, timeout=10); c.row_factory = sqlite3.Row; return c


def initialize_database():
    c = get_db_connection()
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content_type TEXT, content TEXT,
        issues TEXT, suggestions TEXT, analysis TEXT, status TEXT DEFAULT 'Pending',
        created_at TEXT, gemini_success INTEGER DEFAULT 0, gemini_message TEXT,
        compliance_score INTEGER DEFAULT 100, report_json TEXT, visual_analysis TEXT)''')
    columns = {r['name'] for r in c.execute('PRAGMA table_info(reviews)').fetchall()}
    additions = {'analysis':'TEXT', 'gemini_success':'INTEGER DEFAULT 0', 'gemini_message':'TEXT',
                 'compliance_score':'INTEGER DEFAULT 100', 'report_json':'TEXT', 'visual_analysis':'TEXT'}
    for name, typ in additions.items():
        if name not in columns: c.execute(f'ALTER TABLE reviews ADD COLUMN {name} {typ}')
    c.execute('''CREATE TABLE IF NOT EXISTS review_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, review_id INTEGER NOT NULL,
        event TEXT NOT NULL, details TEXT, created_at TEXT NOT NULL)''')
    c.commit(); c.close()


def safe_json(value, default):
    try: return json.loads(value) if value else default
    except (ValueError, TypeError): return default


def serialize_review(row):
    keys = set(row.keys())
    return {'id':row['id'], 'title':row['title'] or '', 'content_type':row['content_type'] or 'General',
        'content':row['content'] or '', 'issues':safe_json(row['issues'], []),
        'suggestions':safe_json(row['suggestions'], []), 'analysis':row['analysis'] or '',
        'status':row['status'] or 'Pending', 'created_at':row['created_at'] or '',
        'gemini_success':bool(row['gemini_success']), 'gemini_message':row['gemini_message'] or '',
        'compliance_score':row['compliance_score'] if 'compliance_score' in keys else 100,
        'report':safe_json(row['report_json'], {}) if 'report_json' in keys else {},
        'visual_analysis':safe_json(row['visual_analysis'], {}) if 'visual_analysis' in keys else {}}


def json_error(message, status=400): return jsonify({'success':False,'message':message}), status


def decode_image(data_url):
    if not data_url: return None
    if not isinstance(data_url, str) or not data_url.startswith('data:image/'):
        raise ValueError('Invalid image format. Please upload a JPG, PNG or WebP image.')
    try:
        header, encoded = data_url.split(',', 1)
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 5 * 1024 * 1024: raise ValueError('Each image must be smaller than 5 MB.')
        image = Image.open(io.BytesIO(raw)); image.verify()
        image = Image.open(io.BytesIO(raw)).convert('RGB')
        if image.width > 5000 or image.height > 5000: raise ValueError('Image dimensions are too large (maximum 5000 × 5000).')
        return image
    except Exception as exc:
        if isinstance(exc, ValueError): raise
        raise ValueError('Could not read the uploaded image. Use a valid JPG, PNG or WebP file.')


def palette_from_image(image, count=5):
    if image is None: return []
    small = image.copy(); small.thumbnail((160,160))
    colors = small.quantize(colors=count, method=Image.Quantize.MEDIANCUT).convert('RGB').getcolors(160*160) or []
    colors.sort(reverse=True)
    total = sum(n for n,_ in colors) or 1
    return [{'hex':'#%02X%02X%02X'%rgb, 'share':round(n*100/total,1)} for n,rgb in colors[:count]]


def hex_rgb(value):
    m = re.fullmatch(r'#?([0-9a-fA-F]{6})', str(value).strip())
    return tuple(int(m.group(1)[i:i+2],16) for i in (0,2,4)) if m else None


def visual_checks(image, logo, guidelines):
    if image is None: return {'status':'Not provided','palette':[],'checks':[],'message':'No creative image was uploaded. Visual checks were skipped.'}
    palette = palette_from_image(image)
    checks=[]; expected = [hex_rgb(x) for x in split_items(guidelines.get('brandColors'))]
    expected = [x for x in expected if x]
    if expected:
        observed = [hex_rgb(x['hex']) for x in palette]
        # Approximate nearest RGB distance, not a perceptual or pixel-perfect guarantee.
        distances = [min(sum((a-b)**2 for a,b in zip(color, target))**0.5 for target in expected) for color in observed]
        matched = sum(1 for d in distances if d <= 65)
        checks.append({'name':'Brand colour presence','status':'Pass' if matched else 'Review','details':f'{matched} of {len(observed)} dominant colours are reasonably close to the configured brand palette.'})
    else:
        checks.append({'name':'Brand colour presence','status':'Not configured','details':'Add approved HEX colours in Brand Guidelines to enable palette comparison.'})
    if logo is not None:
        try:
            a=image.copy(); b=logo.copy(); a.thumbnail((96,96)); b.thumbnail((96,96))
            canvas_a=Image.new('RGB',(96,96),'white'); canvas_b=Image.new('RGB',(96,96),'white')
            canvas_a.paste(a,((96-a.width)//2,(96-a.height)//2)); canvas_b.paste(b,((96-b.width)//2,(96-b.height)//2))
            diff=ImageStat.Stat(ImageChops.difference(canvas_a,canvas_b)).mean
            similarity=max(0,round(100-(sum(diff)/3)/255*100))
            checks.append({'name':'Logo similarity (approximate)','status':'Review' if similarity < 75 else 'Possible match','details':f'Basic resized-pixel similarity estimate: {similarity}%. Different crops, backgrounds or sizes can affect this estimate.'})
        except Exception: checks.append({'name':'Logo comparison','status':'Review','details':'The logo image could not be compared reliably.'})
    else:
        checks.append({'name':'Logo verification','status':'Not configured','details':'Upload the approved logo in Brand Guidelines to enable an approximate comparison.'})
    return {'status':'Completed','palette':palette,'checks':checks,'message':'Automated visual checks are indicative. A human reviewer should confirm logo placement and visual identity.'}


def calculate_score(issues, visual):
    penalties={'High':18,'Medium':10,'Low':4,'Info':0}
    score=100-sum(penalties.get(str(x.get('severity','Medium')).title(),6) for x in issues if isinstance(x,dict))
    for check in visual.get('checks',[]):
        if check.get('status')=='Review': score-=8
    return max(0,min(100,score))


def validate_content(data):
    if not isinstance(data,dict): return None,json_error('Invalid request data.')
    title=str(data.get('title','')).strip(); content=str(data.get('content','')).strip()
    content_type=str(data.get('content_type','General')).strip() or 'General'
    if not title:return None,json_error('Please enter a content title.')
    if not content:return None,json_error('Please enter content to analyze.')
    guidelines=data.get('guidelines',{}); guidelines=guidelines if isinstance(guidelines,dict) else {}
    try:
        image=decode_image(data.get('image_data')); logo=decode_image(data.get('logo_reference_data'))
    except ValueError as exc:return None,json_error(str(exc))
    return {'title':title,'content':content,'content_type':content_type,'guidelines':guidelines,'image':image,'logo':logo},None


def perform_analysis(data):
    rule_issues, rule_suggestions=analyze_brand_content(data['content'],data['guidelines'])
    visual=visual_checks(data['image'],data['logo'],data['guidelines'])
    ai_guidelines={k:v for k,v in data['guidelines'].items() if k != 'logoReferenceData'}
    gemini=analyze_with_gemini(data['content'],data['title'],data['content_type'],ai_guidelines, image=data['image'])
    ai_issues=gemini.get('issues',[]); ai_suggestions=gemini.get('suggestions',[])
    issues=rule_issues+ai_issues
    # De-duplicate by issue title and explanation.
    unique=[]; seen=set()
    for item in issues:
        key=(str(item.get('issue','')).casefold(),str(item.get('explanation',item.get('description',''))).casefold())
        if key not in seen:seen.add(key);unique.append(item)
    suggestions=list(dict.fromkeys(rule_suggestions+ai_suggestions))
    score=calculate_score(unique,visual)
    report={'score':score,'grade':'Excellent' if score>=90 else 'Good' if score>=75 else 'Needs Review' if score>=55 else 'High Risk',
        'issue_count':len(unique),'high_severity':sum(1 for x in unique if isinstance(x,dict) and x.get('severity')=='High'),
        'generated_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'sections':[
            {'name':'Text and brand rules','result':f'{len(rule_issues)} finding(s)'},
            {'name':'Gemini AI review','result':'Completed' if gemini.get('success') else 'Unavailable; rule checks retained'},
            {'name':'Visual brand review','result':visual.get('status','Not provided')}]}
    return {'issues':unique,'suggestions':suggestions,'analysis':gemini.get('analysis',''),'gemini_success':gemini.get('success',False),
        'gemini_message':gemini.get('message',''),'compliance_score':score,'report':report,'visual_analysis':visual}


def record_event(c, review_id, event, details=''):
    c.execute('INSERT INTO review_events(review_id,event,details,created_at) VALUES(?,?,?,?)',
        (review_id,event,details,datetime.now().strftime('%Y-%m-%d %H:%M:%S')))


@app.route('/')
def home(): return render_template('index.html')


@app.route('/analyze',methods=['POST'])
def analyze():
    try:
        data,error=validate_content(request.get_json(silent=True) or {})
        if error:return error
        result=perform_analysis(data); now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c=get_db_connection(); cur=c.execute('''INSERT INTO reviews(title,content_type,content,issues,suggestions,analysis,status,created_at,gemini_success,gemini_message,compliance_score,report_json,visual_analysis)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(data['title'],data['content_type'],data['content'],json.dumps(result['issues']),json.dumps(result['suggestions']),result['analysis'],'Pending',now,int(result['gemini_success']),result['gemini_message'],result['compliance_score'],json.dumps(result['report']),json.dumps(result['visual_analysis'])))
        rid=cur.lastrowid;record_event(c,rid,'Created','Content submitted and analyzed.');c.commit();row=c.execute('SELECT * FROM reviews WHERE id=?',(rid,)).fetchone();c.close()
        return jsonify({'success':True,'message':'Content analyzed successfully.','review':serialize_review(row)})
    except Exception as exc:app.logger.exception('Analyze failed');return json_error('Analysis failed: '+str(exc),500)


@app.route('/review/<int:review_id>',methods=['PUT'])
def edit_review(review_id):
    try:
        data,error=validate_content(request.get_json(silent=True) or {})
        if error:return error
        result=perform_analysis(data);c=get_db_connection();existing=c.execute('SELECT id FROM reviews WHERE id=?',(review_id,)).fetchone()
        if not existing:c.close();return json_error('Review not found.',404)
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''UPDATE reviews SET title=?,content_type=?,content=?,issues=?,suggestions=?,analysis=?,status='Pending',created_at=?,gemini_success=?,gemini_message=?,compliance_score=?,report_json=?,visual_analysis=? WHERE id=?''',
            (data['title'],data['content_type'],data['content'],json.dumps(result['issues']),json.dumps(result['suggestions']),result['analysis'],now,int(result['gemini_success']),result['gemini_message'],result['compliance_score'],json.dumps(result['report']),json.dumps(result['visual_analysis']),review_id))
        record_event(c,review_id,'Re-analyzed','Content updated and analyzed again; approval reset to Pending.');c.commit();row=c.execute('SELECT * FROM reviews WHERE id=?',(review_id,)).fetchone();c.close()
        return jsonify({'success':True,'message':'Review updated and re-analyzed successfully.','review':serialize_review(row)})
    except Exception as exc:app.logger.exception('Edit failed');return json_error('Review update failed: '+str(exc),500)


@app.route('/review/<int:review_id>',methods=['DELETE'])
def delete_review(review_id):
    c=get_db_connection()
    try:
        cur=c.execute('DELETE FROM reviews WHERE id=?',(review_id,));c.execute('DELETE FROM review_events WHERE review_id=?',(review_id,));c.commit()
        if not cur.rowcount:return json_error('Review not found.',404)
        return jsonify({'success':True,'message':'Review deleted successfully.'})
    except Exception as exc:app.logger.exception('Delete failed');return json_error('Review deletion failed: '+str(exc),500)
    finally:c.close()


@app.route('/approve/<int:review_id>',methods=['POST'])
def approve_review(review_id):
    c=get_db_connection()
    try:
        cur=c.execute("UPDATE reviews SET status='Approved' WHERE id=? AND status='Pending'",(review_id,))
        if not cur.rowcount:c.rollback();return json_error('Review not found or already approved.',404)
        record_event(c,review_id,'Approved','Human reviewer approved this review.');c.commit()
        return jsonify({'success':True,'message':'Content approved successfully.'})
    except Exception as exc:app.logger.exception('Approve failed');return json_error('Approval failed: '+str(exc),500)
    finally:c.close()


@app.route('/reviews',methods=['GET'])
def get_reviews():
    c=get_db_connection()
    try:return jsonify([serialize_review(r) for r in c.execute('SELECT * FROM reviews ORDER BY id DESC').fetchall()])
    except Exception as exc:app.logger.exception('Reviews failed');return json_error('Could not load reviews: '+str(exc),500)
    finally:c.close()


@app.route('/review/<int:review_id>/events',methods=['GET'])
def review_events(review_id):
    c=get_db_connection()
    try:
        rows=c.execute('SELECT event,details,created_at FROM review_events WHERE review_id=? ORDER BY id DESC',(review_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:c.close()


@app.errorhandler(413)
def too_large(_):return json_error('Upload too large. Keep each image below 5 MB and total request below 8 MB.',413)
@app.errorhandler(404)
def not_found(_):return json_error('Requested API route was not found.',404)
@app.errorhandler(500)
def server_error(_):app.logger.exception('Internal server error');return json_error('Internal server error.',500)

initialize_database()
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
