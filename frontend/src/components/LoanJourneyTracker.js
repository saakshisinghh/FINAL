import React from 'react';
import { CheckCircle2, Circle, Clock, AlertCircle } from 'lucide-react';
import { Card, CardContent } from './ui/card';

export const LoanJourneyTracker = ({ user, currentStage = 'registration' }) => {
  const verification = user?.verification || {};
  const financialProfile = user?.financial_profile || {};

  const stages = [
    {
      id: 'registration',
      label: 'Registration',
      description: 'Account created',
      completed: true,
    },
    {
      id: 'verification',
      label: 'Identity Verification',
      description: 'Phone & Email OTP',
      completed: verification.phone_verified && verification.email_verified,
      inProgress: !verification.phone_verified || !verification.email_verified,
    },
    {
      id: 'financial_profile',
      label: 'Financial Profile',
      description: 'Income & Employment',
      completed: financialProfile.monthly_income > 0,
      inProgress: !financialProfile.monthly_income && verification.phone_verified && verification.email_verified,
    },
    {
      id: 'need_discovery',
      label: 'Need Discovery',
      description: 'Loan requirements',
      completed: currentStage === 'loan_application' || currentStage === 'approved',
      inProgress: currentStage === 'need_discovery',
    },
    {
      id: 'underwriting',
      label: 'Credit Evaluation',
      description: 'Affordability check',
      completed: currentStage === 'approved',
      inProgress: currentStage === 'underwriting',
    },
    {
      id: 'approval',
      label: 'Loan Approval',
      description: 'Sanction letter',
      completed: currentStage === 'approved',
      inProgress: false,
    },
  ];

  const getStageIcon = (stage) => {
    if (stage.completed) {
      return <CheckCircle2 className="h-6 w-6 text-green-600" data-testid={`stage-${stage.id}-completed`} />;
    } else if (stage.inProgress) {
      return <Clock className="h-6 w-6 text-teal-600 animate-pulse" data-testid={`stage-${stage.id}-inprogress`} />;
    } else {
      return <Circle className="h-6 w-6 text-slate-300" data-testid={`stage-${stage.id}-pending`} />;
    }
  };

  const completedStages = stages.filter(s => s.completed).length;
  const progressPercentage = (completedStages / stages.length) * 100;

  return (
    <Card data-testid="loan-journey-tracker">
      <CardContent className="p-6">
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-slate-900">Loan Journey Progress</h3>
            <span className="text-sm font-medium text-teal-600" data-testid="progress-percentage">
              {completedStages} of {stages.length} completed
            </span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-2">
            <div
              className="bg-gradient-to-r from-teal-600 to-teal-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progressPercentage}%` }}
              data-testid="progress-bar"
            ></div>
          </div>
        </div>

        <div className="space-y-4">
          {stages.map((stage, index) => (
            <div key={stage.id} className="flex items-start space-x-4" data-testid={`stage-${stage.id}`}>
              <div className="relative">
                {getStageIcon(stage)}
                {index < stages.length - 1 && (
                  <div
                    className={`absolute left-1/2 top-8 w-0.5 h-12 -translate-x-1/2 ${
                      stage.completed ? 'bg-green-600' : 'bg-slate-200'
                    }`}
                  ></div>
                )}
              </div>
              <div className="flex-1 pb-8">
                <h4
                  className={`font-medium ${
                    stage.completed
                      ? 'text-green-900'
                      : stage.inProgress
                      ? 'text-teal-900'
                      : 'text-slate-400'
                  }`}
                >
                  {stage.label}
                </h4>
                <p
                  className={`text-sm ${
                    stage.completed
                      ? 'text-green-700'
                      : stage.inProgress
                      ? 'text-teal-700'
                      : 'text-slate-400'
                  }`}
                >
                  {stage.description}
                </p>
                {stage.inProgress && (
                  <div className="mt-2 flex items-center space-x-1 text-xs text-teal-600">
                    <AlertCircle className="h-3 w-3" />
                    <span>Action required</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default LoanJourneyTracker;
