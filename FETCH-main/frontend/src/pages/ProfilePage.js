import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { formatCurrency } from '../lib/utils';
import { User, Mail, Phone, MapPin, Calendar, CreditCard, TrendingUp, Award, Home, Shield } from 'lucide-react';
import OTPVerification from '../components/OTPVerification';
import FinancialProfileForm from '../components/FinancialProfileForm';
import AffordabilityCalculator from '../components/AffordabilityCalculator';

export const ProfilePage = () => {
  const { user, refreshUser } = useAuth();
  const [showAffordability, setShowAffordability] = useState(false);

  const creditScoreColor = 
    user.credit_score >= 800 ? '#0D9488' : 
    user.credit_score >= 700 ? '#F59E0B' : '#EF4444';

  const getCreditRating = (score) => {
    if (score >= 800) return { rating: 'Excellent', description: 'You have an excellent credit profile' };
    if (score >= 750) return { rating: 'Very Good', description: 'You have a very good credit profile' };
    if (score >= 700) return { rating: 'Good', description: 'You have a good credit profile' };
    return { rating: 'Fair', description: 'Consider improving your credit score' };
  };

  const rating = getCreditRating(user.credit_score);

  const verification = user?.verification || {};
  const verificationProgress = [
    verification.phone_verified,
    verification.email_verified,
    verification.kyc_verified
  ].filter(Boolean).length * 33.33;

  return (
    <Layout>
      <div className="space-y-6" data-testid="profile-page">
        <div>
          <h1 className="text-3xl font-bold text-slate-900" data-testid="profile-heading">My Profile</h1>
          <p className="text-slate-600 mt-1">Manage your personal and financial information</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Profile Info */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-2 space-y-6"
          >
            <Card data-testid="personal-info-card">
              <CardHeader>
                <CardTitle>Personal Information</CardTitle>
                <CardDescription>Your basic profile details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="h-12 w-12 rounded-full bg-slate-900 text-white flex items-center justify-center">
                    <User className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-slate-500">Full Name</p>
                    <p className="font-semibold text-slate-900">{user.full_name}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex items-center space-x-3">
                    <Mail className="h-5 w-5 text-slate-400" />
                    <div>
                      <p className="text-sm text-slate-500">Email</p>
                      <p className="text-sm font-medium text-slate-900">{user.email}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <Phone className="h-5 w-5 text-slate-400" />
                    <div>
                      <p className="text-sm text-slate-500">Phone</p>
                      <p className="text-sm font-medium text-slate-900">{user.phone}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <Home className="h-5 w-5 text-slate-400" />
                    <div>
                      <p className="text-sm text-slate-500">City</p>
                      <p className="text-sm font-medium text-slate-900">{user.city}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <Calendar className="h-5 w-5 text-slate-400" />
                    <div>
                      <p className="text-sm text-slate-500">Age</p>
                      <p className="text-sm font-medium text-slate-900">{user.age} years</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* OTP Verification */}
            <OTPVerification user={user} onVerificationComplete={refreshUser} />

            {/* Financial Profile Form */}
            <FinancialProfileForm user={user} onProfileUpdate={refreshUser} />

            {/* Affordability Calculator */}
            <AffordabilityCalculator user={user} />
          </motion.div>

          {/* Sidebar */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            {/* Credit Score */}
            <Card className="border-teal-200">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <CreditCard className="h-5 w-5 text-teal-600" />
                  <span>Credit Score</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center">
                  <div 
                    className="text-5xl font-bold mb-2"
                    style={{ color: creditScoreColor }}
                    data-testid="credit-score-value"
                  >
                    {user.credit_score}
                  </div>
                  <p className="text-sm text-slate-500 mb-4">out of 900</p>
                  
                  <Progress 
                    value={(user.credit_score / 900) * 100} 
                    className="h-2 mb-4"
                    style={{ backgroundColor: '#E2E8F0' }}
                  />
                  
                  <div className="bg-teal-50 rounded-lg p-3">
                    <p className="font-semibold text-teal-900">{rating.rating}</p>
                    <p className="text-xs text-teal-700 mt-1">{rating.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Verification Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="h-5 w-5 text-teal-600" />
                  <span>Verification Status</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium">Overall Progress</span>
                    <span className="text-sm text-slate-600">{Math.round(verificationProgress)}%</span>
                  </div>
                  <Progress value={verificationProgress} className="h-2" />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2 bg-slate-50 rounded">
                    <span className="text-sm">Phone</span>
                    <span className={`text-xs font-medium px-2 py-1 rounded ${verification.phone_verified ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                      {verification.phone_verified ? 'Verified' : 'Pending'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-slate-50 rounded">
                    <span className="text-sm">Email</span>
                    <span className={`text-xs font-medium px-2 py-1 rounded ${verification.email_verified ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                      {verification.email_verified ? 'Verified' : 'Pending'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-slate-50 rounded">
                    <span className="text-sm">KYC</span>
                    <span className={`text-xs font-medium px-2 py-1 rounded ${verification.kyc_verified ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                      {verification.kyc_verified ? 'Verified' : 'Pending'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Pre-approved Limit */}
            <Card className="bg-gradient-to-br from-teal-600 to-teal-700 text-white">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-white">
                  <Award className="h-5 w-5" />
                  <span>Pre-approved Limit</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold mb-2" data-testid="pre-approved-limit">
                  {formatCurrency(user.pre_approved_limit)}
                </div>
                <p className="text-teal-100 text-sm">
                  Ready for instant approval
                </p>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </Layout>
  );
};

export default ProfilePage;
