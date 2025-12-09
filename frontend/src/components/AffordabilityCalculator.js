import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner';
import { profileAPI } from '../services/api';
import { Calculator, Loader2, AlertCircle, CheckCircle2, TrendingUp, IndianRupee, Clock } from 'lucide-react';

export const AffordabilityCalculator = ({ user }) => {
  const [loading, setLoading] = useState(false);
  const [amount, setAmount] = useState('');
  const [tenure, setTenure] = useState('36');
  const [result, setResult] = useState(null);

  const hasFinancialProfile = user?.financial_profile?.monthly_income;

  // Auto-calculate when amount or tenure changes (debounced)
  useEffect(() => {
    if (amount && parseFloat(amount) > 0 && hasFinancialProfile) {
      const timer = setTimeout(() => {
        calculateAffordability();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [amount, tenure]);

  const calculateAffordability = async () => {
    if (!hasFinancialProfile) {
      return;
    }

    if (!amount || amount <= 0) {
      return;
    }

    setLoading(true);
    try {
      const response = await profileAPI.checkAffordability(parseFloat(amount), parseInt(tenure));
      setResult(response.data);
    } catch (error) {
      toast.error('Failed to calculate affordability');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card data-testid="affordability-calculator">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Calculator className="h-5 w-5 text-teal-600" />
          <span>Affordability Calculator</span>
        </CardTitle>
        <CardDescription>
          Check if a loan amount is affordable based on your income
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!hasFinancialProfile ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <p className="font-medium">Financial profile required</p>
              <p className="mt-1">Please complete your financial profile to use the affordability calculator.</p>
            </div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="calc_amount">Loan Amount (₹)</Label>
                <Input
                  id="calc_amount"
                  type="number"
                  placeholder="e.g., 200000"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  min="10000"
                  step="10000"
                  data-testid="affordability-amount-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="calc_tenure">Tenure (Months)</Label>
                <select
                  id="calc_tenure"
                  value={tenure}
                  onChange={(e) => setTenure(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
                  data-testid="affordability-tenure-select"
                >
                  <option value="12">12 months</option>
                  <option value="24">24 months</option>
                  <option value="36">36 months</option>
                  <option value="48">48 months</option>
                  <option value="60">60 months</option>
                </select>
              </div>
            </div>

            <Button
              onClick={calculateAffordability}
              className="w-full bg-teal-600 hover:bg-teal-700"
              disabled={loading || !amount}
              data-testid="calculate-affordability-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Calculating...
                </>
              ) : (
                'Calculate Affordability'
              )}
            </Button>
          </>
        )}

        {result && (
          <div className="space-y-4 mt-6">
            <div
              className={`p-4 rounded-lg border-2 ${
                result.is_affordable
                  ? 'bg-green-50 border-green-300'
                  : 'bg-red-50 border-red-300'
              }`}
              data-testid="affordability-result"
            >
              <div className="flex items-center space-x-2 mb-3">
                {result.is_affordable ? (
                  <>
                    <CheckCircle2 className="h-6 w-6 text-green-600" />
                    <h3 className="font-bold text-green-900">Affordable! ✓</h3>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-6 w-6 text-red-600" />
                    <h3 className="font-bold text-red-900">Not Affordable</h3>
                  </>
                )}
              </div>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center space-x-2">
                    <IndianRupee className="h-4 w-4 text-slate-600" />
                    <div>
                      <p className="text-slate-600">Monthly EMI</p>
                      <p className="font-semibold text-lg">₹{result.proposed_emi?.toLocaleString('en-IN')}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-slate-600" />
                    <div>
                      <p className="text-slate-600">Total EMI</p>
                      <p className="font-semibold text-lg">₹{result.total_emi?.toLocaleString('en-IN')}</p>
                    </div>
                  </div>
                </div>

                {/* EMI Percentage Bar */}
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">EMI as % of Income</span>
                    <span className={`font-semibold ${result.emi_percentage > result.max_emi_percentage ? 'text-red-600' : 'text-green-600'}`}>
                      {result.emi_percentage?.toFixed(1)}% / {result.max_emi_percentage}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full transition-all ${
                        result.emi_percentage > result.max_emi_percentage
                          ? 'bg-red-500'
                          : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min((result.emi_percentage / result.max_emi_percentage) * 100, 100)}%` }}
                    ></div>
                  </div>
                </div>

                {/* DTI Ratio Bar */}
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">Debt-to-Income Ratio</span>
                    <span className={`font-semibold ${result.dti_ratio > result.max_dti_ratio ? 'text-red-600' : 'text-green-600'}`}>
                      {result.dti_ratio?.toFixed(1)}% / {result.max_dti_ratio}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full transition-all ${
                        result.dti_ratio > result.max_dti_ratio
                          ? 'bg-red-500'
                          : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min((result.dti_ratio / result.max_dti_ratio) * 100, 100)}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            {!result.is_affordable && result.max_affordable_loan > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                <div className="flex items-start space-x-3">
                  <TrendingUp className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div className="text-sm text-blue-900">
                    <p className="font-medium">Recommended Amount</p>
                    <p className="mt-1 text-lg font-bold">₹{result.max_affordable_loan?.toLocaleString('en-IN')}</p>
                    <p className="mt-1 text-xs">
                      This is the maximum amount you can comfortably afford based on your income and existing obligations.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="text-xs text-slate-500 space-y-1">
              <p>• EMI should not exceed {result.max_emi_percentage}% of monthly income</p>
              <p>• Total debt should not exceed {result.max_dti_ratio}% of annual income</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AffordabilityCalculator;
