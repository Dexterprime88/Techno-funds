import unittest
import pandas as pd
import numpy as np
from gamma_utils import black_scholes_gamma, calculate_gex, calculate_net_gamma_profile, find_zero_gamma_level

class TestGammaUtils(unittest.TestCase):

    def test_black_scholes_gamma(self):
        # Known value test roughly
        # S=100, K=100, T=1, r=0.05, sigma=0.2
        # d1 = (ln(1) + (0.05 + 0.02)*1) / 0.2 = 0.07 / 0.2 = 0.35
        # Gamma = pdf(0.35) / (100 * 0.2 * 1) = 0.3752 / 20 = 0.01876
        gamma = black_scholes_gamma(100, 100, 1, 0.05, 0.2, 'call')
        self.assertAlmostEqual(gamma, 0.01876, places=3)

    def test_calculate_net_gamma_profile(self):
        # Create dummy data
        data = {
            'StrikePrice': [100, 110],
            'OptionType': ['call', 'put'],
            'IV': [0.2, 0.2],
            'OpenInterest': [1000, 1000],
            'ExpirationDate': [pd.Timestamp.now() + pd.Timedelta(days=30)] * 2
        }
        df = pd.DataFrame(data)

        # Current Spot 105
        current_spot = 105

        # Calculate profile
        profile = calculate_net_gamma_profile(df, current_spot, spot_range_pct=0.1, steps=10)

        self.assertFalse(profile.empty)
        self.assertIn('SpotPrice', profile.columns)
        self.assertIn('TotalGEX', profile.columns)

    def test_find_zero_gamma_level(self):
        # Create a profile that crosses zero
        profile_data = {
            'SpotPrice': [100, 101, 102],
            'TotalGEX': [-100, 50, 200]
        }
        df = pd.DataFrame(profile_data)

        zeros = find_zero_gamma_level(df)
        self.assertEqual(len(zeros), 1)
        self.assertTrue(100 < zeros[0] < 101)

if __name__ == '__main__':
    unittest.main()
