import unittest
from rules_engine import analyze_brand_content

class BrandRulesTests(unittest.TestCase):
    def test_restricted_and_high_risk_claims(self):
        issues, suggestions = analyze_brand_content(
            'GUARANTEED! Our product is 100% risk-free and unlimited. Buy now!!!',
            {'restrictedWords':'guaranteed, unlimited', 'approvedKeywords':'reliable, transparent', 'brandTone':'Professional'}
        )
        names = [item['issue'] for item in issues]
        self.assertIn('Restricted term', names)
        self.assertIn('Absolute or high-risk claim', names)
        self.assertIn('Approved keyword missing', names)
        self.assertIn('Excessive capitalization', names)
        self.assertIn('Excessive punctuation', names)
        self.assertTrue(suggestions)

    def test_required_disclaimer(self):
        issues, _ = analyze_brand_content('A clear and useful product description for customers.', {'requiredDisclaimer':'Terms and conditions apply'})
        self.assertIn('Required disclaimer missing', [item['issue'] for item in issues])

    def test_empty_content(self):
        issues, _ = analyze_brand_content('')
        self.assertEqual(issues[0]['issue'], 'Empty content')

if __name__ == '__main__':
    unittest.main()
