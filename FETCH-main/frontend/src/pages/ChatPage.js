import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { chatAPI } from '../services/api';
import { Send, Bot, User as UserIcon, Sparkles, Loader2 } from 'lucide-react';

export const ChatPage = () => {
  const { user } = useAuth();
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    startNewChat();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const startNewChat = async () => {
    try {
      const response = await chatAPI.startChat();
      setSessionId(response.data.session_id);
      setMessages([
        {
          role: 'assistant',
          content: response.data.message,
          agent_name: 'master',
          created_at: new Date().toISOString()
        }
      ]);
    } catch (error) {
      toast.error('Failed to start chat session');
    } finally {
      setInitializing(false);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || !sessionId) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await chatAPI.sendMessage(sessionId, inputMessage);
      const assistantMessage = {
        role: 'assistant',
        content: response.data.message,
        agent_name: response.data.agent,
        created_at: new Date().toISOString()
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      toast.error('Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    'I need a personal loan',
    'What is my pre-approved limit?',
    'Show me loan options',
    'Calculate EMI'
  ];

  const handleQuickAction = (action) => {
    setInputMessage(action);
  };

  if (initializing) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <Loader2 className="h-12 w-12 text-teal-600 animate-spin mx-auto mb-4" />
            <p className="text-slate-600">Initializing AI assistant...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-5xl mx-auto" data-testid="chat-page">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900" data-testid="chat-heading">
            Loan Assistant
          </h1>
          <p className="text-slate-600 mt-1">
            Chat with our AI-powered assistant to get personalized loan recommendations
          </p>
        </div>

        {/* Chat Container */}
        <Card className="h-[600px] flex flex-col" data-testid="chat-container">
          {/* Chat Header */}
          <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white p-4 rounded-t-lg">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 rounded-full bg-teal-600 flex items-center justify-center">
                <Bot className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold" data-testid="assistant-name">Tata Capital AI Assistant</h3>
                <div className="flex items-center space-x-2 text-xs text-teal-300">
                  <div className="h-2 w-2 rounded-full bg-teal-400 animate-pulse"></div>
                  <span>Online</span>
                </div>
              </div>
            </div>
          </div>

          {/* Messages Area */}
          <CardContent className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50" data-testid="messages-area">
            <AnimatePresence>
              {messages.map((message, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  data-testid={`message-${index}`}
                >
                  <div
                    className={`flex items-start space-x-2 max-w-[80%] ${
                      message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                    }`}
                  >
                    <div
                      className={`h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        message.role === 'user'
                          ? 'bg-slate-900 text-white'
                          : 'bg-teal-600 text-white'
                      }`}
                    >
                      {message.role === 'user' ? (
                        <UserIcon className="h-5 w-5" />
                      ) : (
                        <Bot className="h-5 w-5" />
                      )}
                    </div>
                    <div
                      className={`rounded-lg p-4 ${
                        message.role === 'user'
                          ? 'bg-slate-900 text-white'
                          : 'bg-white border border-slate-200'
                      }`}
                    >
                      {message.agent_name && message.agent_name !== 'master' && (
                        <div className="flex items-center space-x-1 text-xs text-teal-600 mb-2">
                          <Sparkles className="h-3 w-3" />
                          <span className="font-medium">
                            {message.agent_name.charAt(0).toUpperCase() + message.agent_name.slice(1)} Agent
                          </span>
                        </div>
                      )}
                      <p className={`text-sm whitespace-pre-wrap ${message.role === 'user' ? 'text-white' : 'text-slate-700'}`}>
                        {message.content}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="flex items-start space-x-2">
                  <div className="h-8 w-8 rounded-full bg-teal-600 text-white flex items-center justify-center">
                    <Bot className="h-5 w-5" />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-lg p-4">
                    <div className="flex space-x-2">
                      <div className="h-2 w-2 bg-teal-600 rounded-full animate-bounce"></div>
                      <div className="h-2 w-2 bg-teal-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="h-2 w-2 bg-teal-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </CardContent>

          {/* Quick Actions */}
          {messages.length <= 2 && (
            <div className="px-6 py-3 border-t border-slate-200 bg-white" data-testid="quick-actions">
              <p className="text-xs text-slate-500 mb-2">Quick actions:</p>
              <div className="flex flex-wrap gap-2">
                {quickActions.map((action, index) => (
                  <button
                    key={index}
                    onClick={() => handleQuickAction(action)}
                    className="text-xs px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-full transition-colors"
                    data-testid={`quick-action-${index}`}
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="p-4 border-t border-slate-200 bg-white rounded-b-lg" data-testid="input-area">
            <form onSubmit={sendMessage} className="flex space-x-2">
              <Input
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Type your message..."
                className="flex-1"
                disabled={loading}
                data-testid="message-input"
              />
              <Button
                type="submit"
                disabled={loading || !inputMessage.trim()}
                className="bg-teal-600 hover:bg-teal-700 text-white px-6"
                data-testid="send-message-btn"
              >
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </form>
          </div>
        </Card>

        {/* Info Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-6"
        >
          <Card className="bg-teal-50 border-teal-200">
            <CardContent className="p-4">
              <div className="flex items-start space-x-3">
                <Sparkles className="h-5 w-5 text-teal-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-teal-900">AI-Powered Loan Processing</p>
                  <p className="text-xs text-teal-700 mt-1">
                    Our Master Agent coordinates with specialized worker agents (Sales, Verification, Underwriting, Sanction) 
                    to provide you with instant loan approvals and personalized service.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </Layout>
  );
};

export default ChatPage;
