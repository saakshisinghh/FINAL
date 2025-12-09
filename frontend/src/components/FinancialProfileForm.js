import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select } from './ui/select';
import { toast } from 'sonner';
import axios from 'axios';
import { DollarSign, Loader2, CheckCircle2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const FinancialProfileForm = ({ user, onProfileUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    monthly_income: '',
    existing_emi: '',
    employment_type: 'salaried'
  });

  useEffect(() => {
    if (user?.financial_profile) {
      setFormData({
        monthly_income: user.financial_profile.monthly_income || '',
        existing_emi: user.financial_profile.existing_emi || 0,
        employment_type: user.financial_profile.employment_type || 'salaried'
      });
    }
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.monthly_income || formData.monthly_income <= 0) {
      toast.error('Please enter a valid monthly income');
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/profile/financial`,
        {
          monthly_income: parseFloat(formData.monthly_income),
          existing_emi: parseFloat(formData.existing_emi) || 0,
          employment_type: formData.employment_type
        },
        {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        }
      );

      toast.success('Financial profile updated successfully!');
      
      if (onProfileUpdate) {
        onProfileUpdate();
      }
    } catch (error) {
      toast.error('Failed to update financial profile');
    } finally {
      setLoading(false);
    }
  };

  const hasProfile = user?.financial_profile?.monthly_income;

  return (
    <Card data-testid="financial-profile-form">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <DollarSign className="h-5 w-5 text-teal-600" />
          <span>Financial Profile</span>
          {hasProfile && user?.financial_profile?.income_verified && (
            <CheckCircle2 className="h-5 w-5 text-green-600" />
          )}
        </CardTitle>
        <CardDescription>
          Help us understand your financial situation to provide better loan recommendations
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="monthly_income">Monthly Income (₹) *</Label>
            <Input
              id="monthly_income"
              type="number"
              placeholder="e.g., 50000"
              value={formData.monthly_income}
              onChange={(e) => setFormData({ ...formData, monthly_income: e.target.value })}
              required
              min="0"
              step="1000"
              data-testid="monthly-income-input"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="existing_emi">Existing Monthly EMI (₹)</Label>
            <Input
              id="existing_emi"
              type="number"
              placeholder="e.g., 5000"
              value={formData.existing_emi}
              onChange={(e) => setFormData({ ...formData, existing_emi: e.target.value })}
              min="0"
              step="500"
              data-testid="existing-emi-input"
            />
            <p className="text-xs text-slate-500">
              Sum of all your existing loan EMIs
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="employment_type">Employment Type *</Label>
            <select
              id="employment_type"
              value={formData.employment_type}
              onChange={(e) => setFormData({ ...formData, employment_type: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500"
              required
              data-testid="employment-type-select"
            >
              <option value="salaried">Salaried</option>
              <option value="self-employed">Self-Employed</option>
              <option value="business">Business Owner</option>
            </select>
          </div>

          <Button
            type="submit"
            className="w-full bg-teal-600 hover:bg-teal-700"
            disabled={loading}
            data-testid="submit-financial-profile-btn"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Updating...
              </>
            ) : (
              hasProfile ? 'Update Profile' : 'Save Profile'
            )}
          </Button>
        </form>

        {hasProfile && (
          <div className="mt-4 p-3 bg-teal-50 border border-teal-200 rounded-md">
            <p className="text-sm text-teal-900">
              <strong>Current Profile:</strong> ₹{user.financial_profile.monthly_income?.toLocaleString('en-IN')} monthly income
              {user.financial_profile.existing_emi > 0 && ` with ₹${user.financial_profile.existing_emi?.toLocaleString('en-IN')} existing EMI`}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default FinancialProfileForm;
