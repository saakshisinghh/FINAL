import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import { dashboardAPI, loanAPI } from '../services/api';
import { formatCurrency } from '../lib/utils';
import {
  TrendingUp,
  DollarSign,
  CreditCard,
  FileText,
  MessageSquare,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

export const DashboardPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, loansRes] = await Promise.all([
        dashboardAPI.getStats(),
        loanAPI.getAll()
      ]);
      setStats(statsRes.data);
      setLoans(loansRes.data.slice(0, 5));
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="spinner mx-auto mb-4" style={{ width: '40px', height: '40px' }}></div>
            <p className="text-slate-600">Loading dashboard...</p>
          </div>
        </div>
      </Layout>
    );
  }

  const creditScoreColor = 
    user.credit_score >= 800 ? '#0D9488' : 
    user.credit_score >= 700 ? '#F59E0B' : '#EF4444';

  const pieData = [
    { name: 'Used', value: stats?.total_borrowed || 0 },
    { name: 'Available', value: stats?.available_credit || 0 }
  ];

  return (
    <Layout>
      <div className="space-y-8" data-testid="dashboard-page">
        {/* Welcome Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-between items-start"
        >
          <div>
            <h1 className="text-4xl font-bold text-slate-900" data-testid="welcome-heading">
              Welcome back, {user?.full_name}!
            </h1>
            <p className="text-slate-600 mt-2">Here's your financial overview</p>
          </div>
          <Button
            onClick={() => navigate('/chat')}
            className="bg-teal-600 hover:bg-teal-700 text-white h-12 px-6"
            data-testid="start-loan-btn"
          >
            <MessageSquare className="mr-2 h-5 w-5" />
            Start Loan Application
            <Sparkles className="ml-2 h-5 w-5" />
          </Button>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card className="card-hover" data-testid="credit-score-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Credit Score</CardTitle>
                <TrendingUp className="h-4 w-4 text-teal-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold" style={{ color: creditScoreColor }}>
                  {user?.credit_score}
                </div>
                <p className="text-xs text-slate-500 mt-1">out of 900</p>
                <Progress value={(user?.credit_score / 900) * 100} className="mt-3" />
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="card-hover" data-testid="pre-approved-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Pre-Approved Limit</CardTitle>
                <CreditCard className="h-4 w-4 text-slate-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-slate-900">{formatCurrency(user?.pre_approved_limit)}</div>
                <p className="text-xs text-teal-600 mt-1">Instant approval available</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card className="card-hover" data-testid="monthly-emi-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Monthly EMI</CardTitle>
                <DollarSign className="h-4 w-4 text-rose-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-slate-900">{formatCurrency(stats?.monthly_emi || 0)}</div>
                <p className="text-xs text-slate-500 mt-1">Total across {stats?.active_loans || 0} loans</p>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <Card className="card-hover" data-testid="total-loans-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Loans</CardTitle>
                <FileText className="h-4 w-4 text-slate-600" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-slate-900">{stats?.total_loans || 0}</div>
                <p className="text-xs text-slate-500 mt-1">{stats?.pending_applications || 0} pending</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Credit Utilization */}
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }}>
            <Card className="h-full" data-testid="credit-utilization-card">
              <CardHeader>
                <CardTitle>Credit Utilization</CardTitle>
                <CardDescription>Your available vs. used credit</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      <Cell fill="#0D9488" />
                      <Cell fill="#E2E8F0" />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="mt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600">Total Borrowed</span>
                    <span className="font-semibold">{formatCurrency(stats?.total_borrowed || 0)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600">Available</span>
                    <span className="font-semibold text-teal-600">{formatCurrency(stats?.available_credit || 0)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Recent Loans */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="lg:col-span-2"
          >
            <Card data-testid="recent-loans-card">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Recent Loan Applications</CardTitle>
                  <CardDescription>Your latest loan requests</CardDescription>
                </div>
                <Button variant="ghost" size="sm" onClick={() => navigate('/loans')} data-testid="view-all-loans-btn">
                  View All
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                {loans.length === 0 ? (
                  <div className="text-center py-12" data-testid="no-loans-message">
                    <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-600">No loan applications yet</p>
                    <Button
                      onClick={() => navigate('/chat')}
                      className="mt-4 bg-teal-600 hover:bg-teal-700"
                      data-testid="apply-first-loan-btn"
                    >
                      Apply for Your First Loan
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {loans.map((loan) => (
                      <div
                        key={loan.id}
                        className="flex items-center justify-between p-4 border border-slate-200 rounded-sm hover:border-teal-500 transition-colors"
                        data-testid={`loan-item-${loan.id}`}
                      >
                        <div className="flex items-center space-x-4">
                          <div className={`p-2 rounded-full ${
                            loan.status === 'approved' ? 'bg-teal-100' :
                            loan.status === 'rejected' ? 'bg-rose-100' :
                            'bg-amber-100'
                          }`}>
                            {loan.status === 'approved' ? (
                              <CheckCircle2 className="h-5 w-5 text-teal-600" />
                            ) : (
                              <Clock className="h-5 w-5 text-amber-600" />
                            )}
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">{formatCurrency(loan.amount)}</p>
                            <p className="text-sm text-slate-500">{loan.tenure_months} months • {loan.interest_rate}% p.a.</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                            loan.status === 'approved' ? 'bg-teal-100 text-teal-700' :
                            loan.status === 'rejected' ? 'bg-rose-100 text-rose-700' :
                            'bg-amber-100 text-amber-700'
                          }`}>
                            {loan.status.charAt(0).toUpperCase() + loan.status.slice(1)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Quick Actions */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}>
          <Card className="bg-gradient-to-r from-slate-900 to-slate-800 text-white" data-testid="quick-actions-card">
            <CardHeader>
              <CardTitle className="text-white">Ready to Apply for a Loan?</CardTitle>
              <CardDescription className="text-slate-300">
                Chat with our AI assistant to get personalized loan recommendations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                onClick={() => navigate('/chat')}
                className="bg-teal-600 hover:bg-teal-700 text-white"
                data-testid="chat-with-assistant-btn"
              >
                <MessageSquare className="mr-2 h-5 w-5" />
                Chat with AI Assistant
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </Layout>
  );
};

export default DashboardPage;
