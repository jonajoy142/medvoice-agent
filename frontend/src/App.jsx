import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Volume2, User, Clock, Calendar, Settings } from 'lucide-react';
import axios from 'axios';

function App() {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [voiceType, setVoiceType] = useState('female');
  const [status, setStatus] = useState('ready');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Generate session ID on mount
    generateSession();
    
    // Check backend health
    checkHealth();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const generateSession = async () => {
    try {
      const response = await axios.get('/api/v1/health');
      if (response.data.status === 'healthy') {
        setSessionId('session_' + Date.now());
      }
    } catch (error) {
      console.error('Failed to connect to backend:', error);
    }
  };

  const checkHealth = async () => {
    try {
      const response = await axios.get('/api/v1/health');
      console.log('Backend health:', response.data);
    } catch (error) {
      console.error('Backend health check failed:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleMicClick = async () => {
    if (isListening || isProcessing) return;

    setIsListening(true);
    setStatus('listening');

    try {
      const response = await axios.post('/api/v1/voice', {
        session_id: sessionId,
        voice_type: voiceType
      });

      const result = response.data;

      // Add user message
      if (result.user_input) {
        setMessages(prev => [...prev, {
          type: 'user',
          content: result.user_input,
          timestamp: new Date().toISOString()
        }]);
      }

      // Add assistant response
      if (result.response) {
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: result.response,
          timestamp: new Date().toISOString(),
          intent: result.intent,
          action: result.action
        }]);
      }

    } catch (error) {
      console.error('Voice processing error:', error);
      
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsListening(false);
      setIsProcessing(false);
      setIsSpeaking(false);
      setStatus('ready');
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'listening':
        return <Mic className="w-4 h-4" />;
      case 'processing':
        return <Clock className="w-4 h-4" />;
      case 'speaking':
        return <Volume2 className="w-4 h-4" />;
      default:
        return <User className="w-4 h-4" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'listening':
        return 'Listening...';
      case 'processing':
        return 'Processing...';
      case 'speaking':
        return 'Speaking...';
      default:
        return 'Ready';
    }
  };

  const getStatusClass = () => {
    switch (status) {
      case 'listening':
        return 'listening';
      case 'processing':
        return 'processing';
      case 'speaking':
        return 'speaking';
      default:
        return 'ready';
    }
  };

  return (
    <div className="min-h-screen bg-dark-50 flex flex-col">
      {/* Header */}
      <header className="bg-dark-100 border-b border-dark-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
              <Mic className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-white">MedVoice AI</h1>
              <p className="text-sm text-gray-400">Hospital Voice Assistant</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Voice Type Selector */}
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-400">Voice:</label>
              <select 
                value={voiceType}
                onChange={(e) => setVoiceType(e.target.value)}
                className="bg-dark-200 text-gray-100 px-3 py-1 rounded border border-dark-300 focus:outline-none focus:border-primary-500"
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </div>
            
            {/* Status Indicator */}
            <div className={`status-indicator ${getStatusClass()}`}>
              {getStatusIcon()}
              <span>{getStatusText()}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col max-w-4xl mx-auto w-full px-6 py-8">
        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto mb-8 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-20 h-20 bg-dark-200 rounded-full flex items-center justify-center mx-auto mb-4">
                <Mic className="w-10 h-10 text-gray-400" />
              </div>
              <h2 className="text-2xl font-semibold text-white mb-2">Welcome to MedVoice AI</h2>
              <p className="text-gray-400 mb-6">Click the microphone button to start speaking</p>
              <div className="text-sm text-gray-500 space-y-1">
                <p>• Say "book appointment" to schedule a visit</p>
                <p>• Say "check availability" to see doctor schedules</p>
                <p>• Provide your OPID for personalized assistance</p>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`chat-message ${message.type}`}
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-dark-300 flex items-center justify-center flex-shrink-0">
                    {message.type === 'user' ? (
                      <User className="w-4 h-4 text-gray-300" />
                    ) : (
                      <Volume2 className="w-4 h-4 text-gray-300" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium mb-1 opacity-70">
                      {message.type === 'user' ? 'You' : 'Assistant'}
                      {message.intent && (
                        <span className="ml-2 text-xs opacity-50">
                          ({message.intent})
                        </span>
                      )}
                    </p>
                    <p className="text-sm leading-relaxed">{message.content}</p>
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Microphone Button */}
        <div className="flex justify-center">
          <button
            onClick={handleMicClick}
            disabled={isListening || isProcessing}
            className={`mic-button ${(isListening || isProcessing) ? (isListening ? 'listening' : 'processing') : ''}`}
          >
            {isListening ? (
              <MicOff className="w-10 h-10" />
            ) : (
              <Mic className="w-10 h-10" />
            )}
          </button>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 flex justify-center gap-4">
          <button className="px-4 py-2 bg-dark-200 hover:bg-dark-300 rounded-lg text-sm text-gray-300 transition-colors">
            <Calendar className="w-4 h-4 inline mr-2" />
            Book Appointment
          </button>
          <button className="px-4 py-2 bg-dark-200 hover:bg-dark-300 rounded-lg text-sm text-gray-300 transition-colors">
            <Clock className="w-4 h-4 inline mr-2" />
            Check Availability
          </button>
          <button className="px-4 py-2 bg-dark-200 hover:bg-dark-300 rounded-lg text-sm text-gray-300 transition-colors">
            <Settings className="w-4 h-4 inline mr-2" />
            Settings
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-dark-100 border-t border-dark-200 px-6 py-4">
        <div className="max-w-4xl mx-auto text-center text-sm text-gray-400">
          <p>MedVoice AI - Powered by advanced voice recognition and AI</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
