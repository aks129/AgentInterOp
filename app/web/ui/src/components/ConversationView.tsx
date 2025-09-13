import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, User, Bot, Loader } from 'lucide-react';

interface Message {
  id: string;
  type: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'processing' | 'completed';
}

const ConversationView: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'system',
      content: 'Healthcare Agent initialized. Ready to process eligibility checks and clinical scenarios.',
      timestamp: new Date(),
      status: 'completed'
    }
  ]);
  const [newMessage, setNewMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!newMessage.trim() || isProcessing) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: newMessage,
      timestamp: new Date(),
      status: 'sent'
    };

    setMessages(prev => [...prev, userMessage]);
    setNewMessage('');
    setIsProcessing(true);

    // Simulate agent processing
    const processingMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'agent',
      content: 'Processing your request...',
      timestamp: new Date(),
      status: 'processing'
    };

    setMessages(prev => [...prev, processingMessage]);

    // Simulate response
    setTimeout(() => {
      const responses = [
        "I'll help you with the eligibility check. Based on the current scenario, please provide the patient's age, sex, and last screening date.",
        "Processing FHIR data for patient eligibility. Checking against BCS-E criteria...",
        "Patient meets eligibility criteria. Age: 56, Sex: Female, Last mammogram: within acceptable timeframe. Generating recommendation...",
        "Eligibility confirmed. The patient qualifies for breast cancer screening under BCS-E guidelines."
      ];

      const responseMessage: Message = {
        id: (Date.now() + 2).toString(),
        type: 'agent',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date(),
        status: 'completed'
      };

      setMessages(prev => prev.slice(0, -1).concat(responseMessage));
      setIsProcessing(false);
    }, 2000);
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'user': return <User className="h-4 w-4" />;
      case 'agent': return <Bot className="h-4 w-4" />;
      default: return <MessageSquare className="h-4 w-4" />;
    }
  };

  const getMessageStyle = (type: string) => {
    switch (type) {
      case 'user': return 'bg-medical-blue text-white ml-8';
      case 'agent': return 'bg-white border border-slate-200 mr-8';
      case 'system': return 'bg-slate-100 text-slate-700 mx-8';
      default: return 'bg-slate-100';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md border border-slate-200 flex flex-col h-96">
      <div className="p-4 border-b border-slate-200 flex items-center space-x-2">
        <MessageSquare className="h-5 w-5 text-medical-blue" />
        <h3 className="text-lg font-semibold text-slate-800">Multi-Agent Conversation</h3>
        {isProcessing && (
          <div className="ml-auto flex items-center space-x-2 text-sm text-slate-600">
            <Loader className="h-4 w-4 animate-spin" />
            <span>Agent processing...</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div key={message.id} className="flex items-start space-x-3">
            <div className={`p-2 rounded-lg ${
              message.type === 'user' ? 'bg-medical-blue' : 
              message.type === 'agent' ? 'bg-slate-100' : 'bg-slate-50'
            }`}>
              {getMessageIcon(message.type)}
            </div>
            <div className="flex-1">
              <div className={`p-3 rounded-lg ${getMessageStyle(message.type)}`}>
                <p className="text-sm">{message.content}</p>
                {message.status === 'processing' && (
                  <div className="mt-2 flex items-center space-x-2">
                    <Loader className="h-3 w-3 animate-spin" />
                    <span className="text-xs text-slate-500">Processing...</span>
                  </div>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-slate-200">
        <div className="flex space-x-2">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Start eligibility check or ask about clinical scenarios..."
            className="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-medical-blue focus:border-transparent"
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            disabled={isProcessing}
          />
          <button
            onClick={handleSend}
            disabled={!newMessage.trim() || isProcessing}
            className="px-4 py-2 bg-medical-blue text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConversationView;