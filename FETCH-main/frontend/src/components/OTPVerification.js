import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { toast } from 'sonner';
import axios from 'axios';
import { CheckCircle2, Mail, Phone, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const OTPVerification = ({ user, onVerificationComplete }) => {
  const [phoneOTP, setPhoneOTP] = useState('');
  const [emailOTP, setEmailOTP] = useState('');
  const [loadingPhone, setLoadingPhone] = useState(false);
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [sentPhone, setSentPhone] = useState(false);
  const [sentEmail, setSentEmail] = useState(false);
  const [demoPhoneOTP, setDemoPhoneOTP] = useState('');
  const [demoEmailOTP, setDemoEmailOTP] = useState('');

  const verification = user?.verification || {};

  const sendOTP = async (type) => {
    const setLoading = type === 'phone' ? setLoadingPhone : setLoadingEmail;
    const setSent = type === 'phone' ? setSentPhone : setSentEmail;
    const setDemoOTP = type === 'phone' ? setDemoPhoneOTP : setDemoEmailOTP;

    setLoading(true);
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/otp/send`,
        { type },
        {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        }
      );

      setSent(true);
      setDemoOTP(response.data.demo_otp);
      toast.success(`OTP sent to your ${type}!`, {
        description: `Demo OTP: ${response.data.demo_otp}`
      });
    } catch (error) {
      toast.error(`Failed to send OTP to ${type}`);
    } finally {
      setLoading(false);
    }
  };

  const verifyOTP = async (type) => {
    const otp = type === 'phone' ? phoneOTP : emailOTP;
    const setLoading = type === 'phone' ? setLoadingPhone : setLoadingEmail;

    if (!otp || otp.length !== 6) {
      toast.error('Please enter a valid 6-digit OTP');
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/otp/verify`,
        { type, otp },
        {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        }
      );

      toast.success(`${type === 'phone' ? 'Phone' : 'Email'} verified successfully! ✓`);
      
      if (type === 'phone') {
        setPhoneOTP('');
        setSentPhone(false);
      } else {
        setEmailOTP('');
        setSentEmail(false);
      }

      if (onVerificationComplete) {
        onVerificationComplete();
      }
    } catch (error) {
      toast.error('Invalid or expired OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card data-testid="otp-verification-card">
      <CardHeader>
        <CardTitle>Verify Your Identity</CardTitle>
        <CardDescription>
          Complete phone and email verification for instant loan approvals
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Phone Verification */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Phone className="h-5 w-5 text-teal-600" />
              <span className="font-medium">Phone: {user?.phone}</span>
            </div>
            {verification.phone_verified ? (
              <div className="flex items-center space-x-1 text-green-600">
                <CheckCircle2 className="h-5 w-5" />
                <span className="text-sm font-medium">Verified</span>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => sendOTP('phone')}
                disabled={loadingPhone}
                data-testid="send-phone-otp-btn"
              >
                {loadingPhone ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  sentPhone ? 'Resend OTP' : 'Send OTP'
                )}
              </Button>
            )}
          </div>

          {sentPhone && !verification.phone_verified && (
            <div className="flex space-x-2">
              <Input
                type="text"
                maxLength={6}
                placeholder="Enter 6-digit OTP"
                value={phoneOTP}
                onChange={(e) => setPhoneOTP(e.target.value.replace(/\D/g, ''))}
                className="flex-1"
                data-testid="phone-otp-input"
              />
              <Button
                onClick={() => verifyOTP('phone')}
                disabled={loadingPhone || phoneOTP.length !== 6}
                data-testid="verify-phone-otp-btn"
              >
                {loadingPhone ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Verify'}
              </Button>
            </div>
          )}

          {demoPhoneOTP && !verification.phone_verified && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 text-sm">
              <p className="font-medium text-yellow-900">Demo Mode - Your OTP: {demoPhoneOTP}</p>
            </div>
          )}
        </div>

        {/* Email Verification */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Mail className="h-5 w-5 text-teal-600" />
              <span className="font-medium">Email: {user?.email}</span>
            </div>
            {verification.email_verified ? (
              <div className="flex items-center space-x-1 text-green-600">
                <CheckCircle2 className="h-5 w-5" />
                <span className="text-sm font-medium">Verified</span>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => sendOTP('email')}
                disabled={loadingEmail}
                data-testid="send-email-otp-btn"
              >
                {loadingEmail ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  sentEmail ? 'Resend OTP' : 'Send OTP'
                )}
              </Button>
            )}
          </div>

          {sentEmail && !verification.email_verified && (
            <div className="flex space-x-2">
              <Input
                type="text"
                maxLength={6}
                placeholder="Enter 6-digit OTP"
                value={emailOTP}
                onChange={(e) => setEmailOTP(e.target.value.replace(/\D/g, ''))}
                className="flex-1"
                data-testid="email-otp-input"
              />
              <Button
                onClick={() => verifyOTP('email')}
                disabled={loadingEmail || emailOTP.length !== 6}
                data-testid="verify-email-otp-btn"
              >
                {loadingEmail ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Verify'}
              </Button>
            </div>
          )}

          {demoEmailOTP && !verification.email_verified && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 text-sm">
              <p className="font-medium text-yellow-900">Demo Mode - Your OTP: {demoEmailOTP}</p>
            </div>
          )}
        </div>

        {/* Verification Complete Message */}
        {verification.phone_verified && verification.email_verified && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <div className="flex items-center space-x-2 text-green-800">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-medium">All verifications complete! You're ready to apply for loans.</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default OTPVerification;
