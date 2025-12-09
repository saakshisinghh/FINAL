import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { loanAPI, sanctionAPI, documentAPI } from '../services/api';
import { formatCurrency, formatDate } from '../lib/utils';
import { FileText, Download, CheckCircle2, XCircle, Clock, AlertCircle, Plus, Upload, File, Trash2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LoansPage = () => {
  const { user, refreshUser } = useAuth();
  const [loans, setLoans] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedLoan, setSelectedLoan] = useState(null);
  
  // Loan application form state
  const [loanForm, setLoanForm] = useState({
    amount: '',
    tenure_months: '12',
    purpose: ''
  });
  const [calculatedEMI, setCalculatedEMI] = useState(null);
  const [applying, setApplying] = useState(false);
  
  // Document upload state
  const [uploadFile, setUploadFile] = useState(null);
  const [docType, setDocType] = useState('salary_slip');
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchLoans();
    fetchDocuments();
  }, []);

  useEffect(() => {
    if (loanForm.amount && loanForm.tenure_months) {
      calculateEMI();
    }
  }, [loanForm.amount, loanForm.tenure_months]);

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

  const fetchDocuments = async () => {
    try {
      const response = await documentAPI.getAll();
      setDocuments(response.data);
    } catch (error) {
      console.error('Failed to load documents', error);
    }
  };

  const calculateEMI = () => {
    const amount = parseFloat(loanForm.amount);
    const months = parseInt(loanForm.tenure_months);
    
    if (!amount || !months || amount <= 0 || months <= 0) {
      setCalculatedEMI(null);
      return;
    }

    // Estimate interest rate based on credit score (similar to backend logic)
    let interestRate = 12.5; // default
    if (user.credit_score >= 800) interestRate = 10.5;
    else if (user.credit_score >= 750) interestRate = 11.5;
    else if (user.credit_score >= 700) interestRate = 12.5;
    else interestRate = 14.0;

    const monthlyRate = interestRate / (12 * 100);
    const emi = amount * monthlyRate * Math.pow(1 + monthlyRate, months) / (Math.pow(1 + monthlyRate, months) - 1);
    const totalPayable = emi * months;

    setCalculatedEMI({
      emi: Math.round(emi * 100) / 100,
      totalPayable: Math.round(totalPayable * 100) / 100,
      interestRate
    });
  };

  const handleApplyLoan = async (e) => {
    e.preventDefault();
    
    const amount = parseFloat(loanForm.amount);
    if (!amount || amount <= 0) {
      toast.error('Please enter a valid loan amount');
      return;
    }
    
    if (amount > user.pre_approved_limit * 2) {
      toast.error(`Maximum eligible amount is ${formatCurrency(user.pre_approved_limit * 2)}`);
      return;
    }

    if (!loanForm.purpose.trim()) {
      toast.error('Please provide a purpose for the loan');
      return;
    }

    setApplying(true);
    try {
      const response = await loanAPI.apply({
        amount: amount,
        tenure_months: parseInt(loanForm.tenure_months),
        purpose: loanForm.purpose
      });

      const result = response.data;
      
      if (result.underwriting_result.status === 'approved') {
        toast.success('🎉 Congratulations! Your loan is approved!');
      } else if (result.underwriting_result.status === 'requires_documents') {
        toast.warning('Please upload required documents to complete your application');
      } else if (result.underwriting_result.status === 'rejected') {
        toast.error(result.underwriting_result.message || 'Loan application rejected');
      }

      setApplyModalOpen(false);
      setLoanForm({ amount: '', tenure_months: '12', purpose: '' });
      setCalculatedEMI(null);
      fetchLoans();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to apply for loan');
    } finally {
      setApplying(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Only PDF and image files (PNG, JPG) are allowed');
      e.target.value = '';
      return;
    }

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File size must be less than 10MB');
      e.target.value = '';
      return;
    }

    setUploadFile(file);
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    
    if (!uploadFile) {
      toast.error('Please select a file to upload');
      return;
    }

    setUploading(true);
    try {
      const response = await documentAPI.upload(uploadFile, docType, selectedLoan?.id);
      
      toast.success(response.data.message || 'Document uploaded successfully');
      
      // Check if loan status was updated
      if (response.data.loan_status_updated) {
        if (response.data.new_loan_status === 'approved') {
          toast.success('🎉 Great news! Your loan has been approved!');
        } else if (response.data.new_loan_status === 'rejected') {
          toast.error('Your loan application was rejected after review');
        }
      }

      setUploadModalOpen(false);
      setUploadFile(null);
      setDocType('salary_slip');
      setSelectedLoan(null);
      fetchLoans();
      fetchDocuments();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    } finally {
      setUploading(false);
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

  const openUploadModal = (loan) => {
    setSelectedLoan(loan);
    setUploadModalOpen(true);
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

  const getLoanDocuments = (loanId) => {
    return documents.filter(doc => doc.loan_application_id === loanId);
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
        {/* Header with Apply Button */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900" data-testid="loans-heading">My Loan Applications</h1>
            <p className="text-slate-600 mt-1">Track and manage your loan applications</p>
          </div>
          
          <Dialog open={applyModalOpen} onOpenChange={setApplyModalOpen}>
            <DialogTrigger asChild>
              <Button className="bg-teal-600 hover:bg-teal-700" data-testid="apply-loan-btn">
                <Plus className="mr-2 h-4 w-4" />
                Apply for Loan
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]" data-testid="apply-loan-modal">
              <DialogHeader>
                <DialogTitle>Apply for Personal Loan</DialogTitle>
                <DialogDescription>
                  Fill in the details to apply for a personal loan. Your pre-approved limit is {formatCurrency(user.pre_approved_limit)}.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleApplyLoan} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="amount">Loan Amount (₹)</Label>
                  <Input
                    id="amount"
                    type="number"
                    placeholder="Enter amount"
                    value={loanForm.amount}
                    onChange={(e) => setLoanForm({ ...loanForm, amount: e.target.value })}
                    min="1000"
                    max={user.pre_approved_limit * 2}
                    step="1000"
                    required
                    data-testid="loan-amount-input"
                  />
                  <p className="text-xs text-slate-500">
                    Maximum eligible: {formatCurrency(user.pre_approved_limit * 2)}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tenure">Loan Tenure</Label>
                  <Select
                    value={loanForm.tenure_months}
                    onValueChange={(value) => setLoanForm({ ...loanForm, tenure_months: value })}
                  >
                    <SelectTrigger data-testid="tenure-select">
                      <SelectValue placeholder="Select tenure" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="6">6 months</SelectItem>
                      <SelectItem value="12">12 months (1 year)</SelectItem>
                      <SelectItem value="18">18 months</SelectItem>
                      <SelectItem value="24">24 months (2 years)</SelectItem>
                      <SelectItem value="36">36 months (3 years)</SelectItem>
                      <SelectItem value="48">48 months (4 years)</SelectItem>
                      <SelectItem value="60">60 months (5 years)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="purpose">Purpose of Loan</Label>
                  <Textarea
                    id="purpose"
                    placeholder="e.g., Home renovation, Medical expenses, Education..."
                    value={loanForm.purpose}
                    onChange={(e) => setLoanForm({ ...loanForm, purpose: e.target.value })}
                    rows={3}
                    required
                    data-testid="loan-purpose-input"
                  />
                </div>

                {calculatedEMI && (
                  <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 space-y-2">
                    <h4 className="font-semibold text-teal-900">Estimated Loan Details</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="text-slate-600">Interest Rate</p>
                        <p className="font-semibold text-slate-900">{calculatedEMI.interestRate}% p.a.</p>
                      </div>
                      <div>
                        <p className="text-slate-600">Monthly EMI</p>
                        <p className="font-semibold text-slate-900">{formatCurrency(calculatedEMI.emi)}</p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-slate-600">Total Amount Payable</p>
                        <p className="font-semibold text-slate-900">{formatCurrency(calculatedEMI.totalPayable)}</p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex justify-end space-x-2 pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setApplyModalOpen(false);
                      setLoanForm({ amount: '', tenure_months: '12', purpose: '' });
                      setCalculatedEMI(null);
                    }}
                    disabled={applying}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    className="bg-teal-600 hover:bg-teal-700"
                    disabled={applying}
                    data-testid="submit-loan-btn"
                  >
                    {applying ? 'Processing...' : 'Apply Now'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Document Upload Modal */}
        <Dialog open={uploadModalOpen} onOpenChange={setUploadModalOpen}>
          <DialogContent className="sm:max-w-[500px]" data-testid="upload-document-modal">
            <DialogHeader>
              <DialogTitle>Upload Documents</DialogTitle>
              <DialogDescription>
                Upload required documents for your loan application. Accepted formats: PDF, PNG, JPG (Max 10MB)
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleUploadDocument} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="docType">Document Type</Label>
                <Select value={docType} onValueChange={setDocType}>
                  <SelectTrigger data-testid="doc-type-select">
                    <SelectValue placeholder="Select document type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="salary_slip">Salary Slip</SelectItem>
                    <SelectItem value="aadhaar">Aadhaar Card</SelectItem>
                    <SelectItem value="pan">PAN Card</SelectItem>
                    <SelectItem value="bank_statement">Bank Statement</SelectItem>
                    <SelectItem value="other">Other Document</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="file">Select File</Label>
                <div className="flex items-center space-x-2">
                  <Input
                    id="file"
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={handleFileChange}
                    className="cursor-pointer"
                    data-testid="file-input"
                  />
                </div>
                {uploadFile && (
                  <div className="flex items-center space-x-2 text-sm text-slate-600">
                    <File className="h-4 w-4" />
                    <span>{uploadFile.name}</span>
                    <span className="text-slate-400">({(uploadFile.size / 1024 / 1024).toFixed(2)} MB)</span>
                  </div>
                )}
              </div>

              <div className="flex justify-end space-x-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setUploadModalOpen(false);
                    setUploadFile(null);
                    setDocType('salary_slip');
                    setSelectedLoan(null);
                  }}
                  disabled={uploading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="bg-teal-600 hover:bg-teal-700"
                  disabled={uploading || !uploadFile}
                  data-testid="upload-submit-btn"
                >
                  {uploading ? 'Uploading...' : 'Upload Document'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Loans List */}
        {loans.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16" data-testid="no-loans">
              <FileText className="h-16 w-16 text-slate-300 mb-4" />
              <h3 className="text-xl font-semibold text-slate-900 mb-2">No loan applications yet</h3>
              <p className="text-slate-600 text-center mb-6">Start your loan journey by applying for a loan or chatting with our AI assistant</p>
              <div className="flex space-x-3">
                <Button className="bg-teal-600 hover:bg-teal-700" onClick={() => setApplyModalOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Apply Now
                </Button>
                <Button variant="outline" onClick={() => window.location.href = '/chat'}>
                  <FileText className="mr-2 h-4 w-4" />
                  Chat Assistant
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {loans.map((loan, index) => {
              const loanDocs = getLoanDocuments(loan.id);
              return (
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
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                        <div>
                          <p className="text-xs text-slate-500 mb-1">Purpose</p>
                          <p className="text-sm text-slate-700">{loan.purpose}</p>
                        </div>
                      )}

                      {loan.rejection_reason && (
                        <div className="bg-rose-50 border border-rose-200 rounded-lg p-3">
                          <p className="text-sm text-rose-700">{loan.rejection_reason}</p>
                        </div>
                      )}

                      {/* Uploaded Documents */}
                      {loanDocs.length > 0 && (
                        <div className="border-t pt-4">
                          <h4 className="text-sm font-semibold text-slate-900 mb-2">Uploaded Documents</h4>
                          <div className="space-y-2">
                            {loanDocs.map((doc) => (
                              <div key={doc.id} className="flex items-center justify-between bg-slate-50 p-2 rounded">
                                <div className="flex items-center space-x-2">
                                  <File className="h-4 w-4 text-slate-500" />
                                  <span className="text-sm text-slate-700">
                                    {doc.doc_type.replace('_', ' ').toUpperCase()}
                                  </span>
                                  <span className="text-xs text-slate-400">
                                    {formatDate(doc.uploaded_at)}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex flex-wrap gap-2 pt-2">
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
                          <Button
                            onClick={() => openUploadModal(loan)}
                            className="bg-amber-600 hover:bg-amber-700 text-white"
                            data-testid={`upload-docs-${loan.id}`}
                          >
                            <Upload className="mr-2 h-4 w-4" />
                            Upload Documents
                          </Button>
                        )}
                      </div>

                      {loan.status === 'requires_documents' && (
                        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                          <p className="text-sm text-amber-700 font-medium">
                            📄 Action Required: Please upload your salary slip and other required documents to proceed with your application.
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default LoansPage;
