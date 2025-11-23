import { useState } from 'react';

/**
 * Simplified ChatInterface for debugging
 */
function ChatInterfaceSimple() {
  const [message, setMessage] = useState('Chat Interface Loaded Successfully!');
  
  return (
    <div className="w-full max-w-4xl mx-auto bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-4">
        💬 Simple Chat Interface
      </h2>
      <p className="text-gray-600 dark:text-gray-300 mb-6">
        {message}
      </p>
      <button
        onClick={() => setMessage('Button clicked! Component is working.')}
        className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors"
      >
        Test Button
      </button>
    </div>
  );
}

export default ChatInterfaceSimple;
