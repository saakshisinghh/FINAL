import React from 'react';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { formatCurrency } from '../lib/utils';
import { User, Mail, Phone, MapPin, Calendar, CreditCard, TrendingUp, Award, Home } from 'lucide-react';

export const ProfilePage = () => {
  const { user } = useAuth();

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
                  <div>
                    <p className="text-sm text-slate-500">Full Name</p>
                    <p className="font-semibold text-slate-900" data-testid="user-fullname">{user.full_name}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex items-start space-x-3">
                    <Mail className="h-5 w-5 text-slate-400 mt-0.5" />
                    <div>
                      <p className="text-sm text-slate-500">Email</p>
                      <p className="text-sm text-slate-900" data-testid="user-email">{user.email}</p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3">
                    <Phone className="h-5 w-5 text-slate-400 mt-0.5" />
                    <div>
                      <p className="text-sm text-slate-500">Phone</p>
                      <p className="text-sm text-slate-900" data-testid="user-phone">{user.phone}</p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3">
                    <Calendar className="h-5 w-5 text-slate-400 mt-0.5" />
                    <div>
                      <p className="text-sm text-slate-500">Age</p>
                      <p className="text-sm text-slate-900" data-testid="user-age">{user.age} years</p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3">
                    <MapPin className="h-5 w-5 text-slate-400 mt-0.5" />
                    <div>
                      <p className="text-sm text-slate-500">City</p>
                      <p className="text-sm text-slate-900" data-testid="user-city">{user.city}</p>
                    </div>
                  </div>
                </div>

                <div className="flex items-start space-x-3 pt-4 border-t border-slate-200">
                  <Home className="h-5 w-5 text-slate-400 mt-0.5" />
                  <div>
                    <p className="text-sm text-slate-500">Address</p>
                    <p className="text-sm text-slate-900" data-testid="user-address">{user.address}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card data-testid="financial-info-card">
              <CardHeader>
                <CardTitle>Financial Information</CardTitle>
                <CardDescription>Your loan eligibility and limits</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-teal-50 rounded-sm">
                  <div className="flex items-center space-x-3">
                    <div className="h-12 w-12 rounded-full bg-teal-600 text-white flex items-center justify-center">
                      <CreditCard className="h-6 w-6" />
                    </div>
                    <div>
                      <p className="text-sm text-slate-600">Pre-Approved Limit</p>
                      <p className="text-2xl font-bold text-slate-900" data-testid="pre-approved-limit">
                        {formatCurrency(user.pre_approved_limit)}
                      </p>
                    </div>
                  </div>
                  <Award className="h-8 w-8 text-teal-600" />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm text-slate-600">Interest Rate Range</p>
                    <p className="text-sm font-semibold text-slate-900">10.5% - 14.0% p.a.</p>
                  </div>
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-600">Maximum Tenure</p>
                    <p className="text-sm font-semibold text-slate-900">60 months</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Credit Score */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <Card className="sticky top-24" data-testid="credit-score-card">
              <CardHeader>
                <CardTitle>Credit Score</CardTitle>
                <CardDescription>Your creditworthiness rating</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center mb-6">
                  <div className="inline-flex items-center justify-center w-32 h-32 rounded-full bg-slate-100 mb-4">
                    <div className="text-center">
                      <p className="text-4xl font-bold" style={{ color: creditScoreColor }} data-testid="credit-score">
                        {user.credit_score}
                      </p>
                      <p className="text-xs text-slate-500">out of 900</p>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xl font-semibold text-slate-900">{rating.rating}</p>
                    <p className="text-sm text-slate-600">{rating.description}</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-slate-600">Score Progress</span>
                      <span className="font-semibold text-slate-900">{Math.round((user.credit_score / 900) * 100)}%</span>
                    </div>
                    <Progress value={(user.credit_score / 900) * 100} />
                  </div>

                  <div className="pt-4 border-t border-slate-200">
                    <p className="text-sm font-medium text-slate-900 mb-3 flex items-center">
                      <TrendingUp className="h-4 w-4 mr-2 text-teal-600" />
                      Score Breakdown
                    </p>
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-600">Poor (300-549)</span>
                        </div>
                        <Progress value={user.credit_score >= 550 ? 100 : ((user.credit_score - 300) / 249) * 100} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-600">Fair (550-649)</span>
                        </div>
                        <Progress value={user.credit_score >= 650 ? 100 : user.credit_score >= 550 ? ((user.credit_score - 550) / 99) * 100 : 0} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-600">Good (650-749)</span>
                        </div>
                        <Progress value={user.credit_score >= 750 ? 100 : user.credit_score >= 650 ? ((user.credit_score - 650) / 99) * 100 : 0} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-600">Excellent (750+)</span>
                        </div>
                        <Progress value={user.credit_score >= 750 ? ((user.credit_score - 750) / 150) * 100 : 0} className="h-2" />
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </Layout>
  );
};

export default ProfilePage;