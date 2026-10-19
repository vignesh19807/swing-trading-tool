import React from 'react';
import { Link } from 'react-router-dom';
import logoImg from '../assets/logo.png';

const NotFound = () => {
  return (
    <div className="p-8 h-full flex flex-col items-center justify-center text-center">
      <img src={logoImg} alt="Swing-tool" className="w-16 h-16 rounded-2xl mb-5 object-contain shadow-md" />
      <h1 className="text-4xl font-heading font-bold mb-4">404 - Page Not Found</h1>
      <p className="text-tx-secondary mb-8">The page you are looking for doesn't exist or has been moved.</p>
      <Link 
        to="/" 
        className="px-6 py-2 bg-accent-green text-deep-navy font-semibold rounded-lg hover:bg-accent-green/90 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-accent-green"
      >
        Return to Dashboard
      </Link>
    </div>
  );
};

export default NotFound;
