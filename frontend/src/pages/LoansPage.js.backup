import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { loanAPI, sanctionAPI } from '../services/api';
import { formatCurrency, formatDate } from '../lib/utils';
import { FileText, Download, CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';

export const LoansPage = () => {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLoans();
  }, []);

  const fetchLoans = async () => {
    try {
      const response = await loanAPI.getAll();
      setLoans(response.data);
    } catch (error) {
      toast.error('Failed to load loans');
    } finally {
      setLoading(false);
    }
  };

  const downloadSanctionLetter = async (loanId) => {
    try {
      const response = await sanctionAPI.download(loanId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `sanction_letter_${loanId.slice(0, 8)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Sanction letter downloaded');
    } catch (error) {
      toast.error('Failed to download sanction letter');
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'approved':
        return <CheckCircle2 className="h-5 w-5 text-teal-600" />;
      case 'rejected':
        return <XCircle className="h-5 w-5 text-rose-600" />;
      case 'requires_documents':
        return <AlertCircle className="h-5 w-5 text-amber-600" />;
      default:
        return <Clock className="h-5 w-5 text-slate-600" />;
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      approved: 'bg-teal-100 text-teal-700',
      rejected: 'bg-rose-100 text-rose-700',
      requires_documents: 'bg-amber-100 text-amber-700',
      pending: 'bg-slate-100 text-slate-700'
    };
    return variants[status] || variants.pending;
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="spinner mx-auto mb-4" style={{ width: '40px', height: '40px' }}></div>
            <p className="text-slate-600">Loading loans...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="loans-page">
        <div>
          <h1 className="text-3xl font-bold text-slate-900" data-testid="loans-heading">My Loan Applications</h1>
          <p className="text-slate-600 mt-1">Track and manage your loan applications</p>
        </div>

        {loans.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16" data-testid="no-loans">
              <FileText className="h-16 w-16 text-slate-300 mb-4" />
              <h3 className="text-xl font-semibold text-slate-900 mb-2">No loan applications yet</h3>
              <p className="text-slate-600 text-center mb-6">Start your loan journey by chatting with our AI assistant</p>
              <Button className="bg-teal-600 hover:bg-teal-700" onClick={() => window.location.href = '/chat'}>
                Apply for a Loan
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {loans.map((loan, index) => (
              <motion.div
                key={loan.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="card-hover" data-testid={`loan-card-${loan.id}`}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3">
                        <div className={`p-2 rounded-full ${loan.status === 'approved' ? 'bg-teal-100' : loan.status === 'rejected' ? 'bg-rose-100' : 'bg-amber-100'}`}>
                          {getStatusIcon(loan.status)}
                        </div>
                        <div>
                          <CardTitle className="text-xl" data-testid={`loan-amount-${loan.id}`}>{formatCurrency(loan.amount)}</CardTitle>
                          <CardDescription data-testid={`loan-date-${loan.id}`}>Applied on {formatDate(loan.created_at)}</CardDescription>
                        </div>
                      </div>
                      <Badge className={getStatusBadge(loan.status)} data-testid={`loan-status-${loan.id}`}>
                        {loan.status.charAt(0).toUpperCase() + loan.status.slice(1).replace('_', ' ')}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                      <div>
                        <p className="text-xs text-slate-500 mb-1">Interest Rate</p>
                        <p className="font-semibold text-slate-900">{loan.interest_rate}% p.a.</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500 mb-1">Tenure</p>
                        <p className="font-semibold text-slate-900">{loan.tenure_months} months</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500 mb-1">Monthly EMI</p>
                        <p className="font-semibold text-slate-900">{formatCurrency(loan.emi)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500 mb-1">Total Payable</p>
                        <p className="font-semibold text-slate-900">{formatCurrency(loan.total_payable)}</p>
                      </div>
                    </div>

                    {loan.purpose && (
                      <div className="mb-4">
                        <p className="text-xs text-slate-500 mb-1">Purpose</p>
                        <p className="text-sm text-slate-700">{loan.purpose}</p>
                      </div>
                    )}

                    {loan.rejection_reason && (
                      <div className="bg-rose-50 border border-rose-200 rounded-sm p-3 mb-4">
                        <p className="text-sm text-rose-700">{loan.rejection_reason}</p>
                      </div>
                    )}

                    {loan.status === 'approved' && (
                      <Button
                        onClick={() => downloadSanctionLetter(loan.id)}
                        className="bg-teal-600 hover:bg-teal-700 text-white"
                        data-testid={`download-sanction-${loan.id}`}
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Download Sanction Letter
                      </Button>
                    )}

                    {loan.status === 'requires_documents' && (
                      <div className="bg-amber-50 border border-amber-200 rounded-sm p-3">
                        <p className="text-sm text-amber-700">Please upload required documents to proceed with your application.</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default LoansPage;