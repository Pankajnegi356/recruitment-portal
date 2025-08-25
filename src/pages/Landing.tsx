import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { ArrowRight, Users, Target, Zap, Shield } from 'lucide-react';

const Landing: React.FC = () => {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    navigate('/login');
  };

  return (
    <div className="h-screen bg-stone-50 overflow-hidden">
      {/* Main Content - Full Viewport */}
      <main className="h-full px-8 flex items-center">
        <div className="max-w-7xl mx-auto w-full">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-center h-full">
            {/* Left Side - Content */}
            <div className="space-y-8">
              {/* Giant Visual Text */}
              <div className="relative">
                <h1 className="text-8xl md:text-9xl font-black text-stone-200 leading-none select-none">
                  HIRE
                </h1>
                <div className="relative -mt-20 ml-8">
                  <h2 className="text-5xl md:text-6xl font-bold text-stone-800 leading-none mb-8">
                    AI-Powered
                    <br />
                    Recruitment
                  </h2>
                  <p className="text-xl text-stone-600 leading-relaxed max-w-lg mb-12">
                    Transform your hiring process with intelligent candidate matching 
                    and automated screening. Find perfect talent faster.
                  </p>
                  
                  <Button 
                    onClick={handleGetStarted}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-10 py-5 text-xl font-semibold rounded-xl shadow-lg transition-all duration-200"
                  >
                    Get Started
                    <ArrowRight className="ml-3 h-6 w-6" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Right Side - Minimalist Recruitment Visual */}
            <div className="hidden lg:flex items-center justify-center h-full relative">
              <div className="relative w-96 h-96">
                {/* Central Profile Circle - representing candidates */}
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-24 h-24 bg-gradient-to-br from-blue-100 to-blue-200 rounded-full opacity-80 shadow-lg">
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-blue-300 rounded-full"></div>
                  <div className="absolute top-3/4 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-12 h-6 bg-blue-300 rounded-full"></div>
                </div>
                
                {/* Connecting Lines - representing recruitment flow */}
                <div className="absolute top-1/2 left-1/4 w-16 h-0.5 bg-gradient-to-r from-stone-300 to-blue-200 transform -translate-y-1/2"></div>
                <div className="absolute top-1/2 right-1/4 w-16 h-0.5 bg-gradient-to-l from-stone-300 to-blue-200 transform -translate-y-1/2"></div>
                <div className="absolute top-1/4 left-1/2 w-0.5 h-16 bg-gradient-to-b from-stone-300 to-blue-200 transform -translate-x-1/2"></div>
                <div className="absolute bottom-1/4 left-1/2 w-0.5 h-16 bg-gradient-to-t from-stone-300 to-blue-200 transform -translate-x-1/2"></div>
                
                {/* Corner Elements - representing different stages */}
                {/* Resume/CV */}
                <div className="absolute top-16 left-16 w-12 h-16 bg-gradient-to-br from-emerald-100 to-emerald-200 rounded-sm opacity-70 shadow-md">
                  <div className="absolute top-2 left-2 w-8 h-0.5 bg-emerald-400 rounded"></div>
                  <div className="absolute top-4 left-2 w-6 h-0.5 bg-emerald-400 rounded"></div>
                  <div className="absolute top-6 left-2 w-8 h-0.5 bg-emerald-400 rounded"></div>
                </div>
                
                {/* Interview */}
                <div className="absolute top-16 right-16 w-16 h-12 bg-gradient-to-br from-amber-100 to-amber-200 rounded-lg opacity-70 shadow-md">
                  <div className="absolute top-2 left-2 w-4 h-4 bg-amber-400 rounded-full"></div>
                  <div className="absolute top-2 right-2 w-4 h-4 bg-amber-400 rounded-full"></div>
                  <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 w-8 h-1 bg-amber-400 rounded"></div>
                </div>
                
                {/* Job Offer */}
                <div className="absolute bottom-16 right-16 w-14 h-14 bg-gradient-to-br from-rose-100 to-rose-200 rounded-full opacity-70 shadow-md">
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-6 h-4 bg-rose-400 rounded-sm"></div>
                </div>
                
                {/* Analytics/Reports */}
                <div className="absolute bottom-16 left-16 w-16 h-12 bg-gradient-to-br from-purple-100 to-purple-200 rounded-lg opacity-70 shadow-md">
                  <div className="absolute bottom-2 left-1 w-2 h-6 bg-purple-400 rounded-sm"></div>
                  <div className="absolute bottom-2 left-4 w-2 h-4 bg-purple-400 rounded-sm"></div>
                  <div className="absolute bottom-2 left-7 w-2 h-8 bg-purple-400 rounded-sm"></div>
                  <div className="absolute bottom-2 right-2 w-2 h-3 bg-purple-400 rounded-sm"></div>
                </div>
                
                {/* Subtle floating dots for depth */}
                <div className="absolute top-8 left-1/2 w-2 h-2 bg-stone-300 rounded-full opacity-50 animate-pulse" style={{animationDuration: '3s'}}></div>
                <div className="absolute bottom-8 left-1/3 w-1.5 h-1.5 bg-stone-300 rounded-full opacity-40 animate-pulse" style={{animationDuration: '4s', animationDelay: '1s'}}></div>
                <div className="absolute top-1/3 right-8 w-1.5 h-1.5 bg-stone-300 rounded-full opacity-40 animate-pulse" style={{animationDuration: '5s', animationDelay: '2s'}}></div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Minimal Footer */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2">
        <p className="text-xs text-stone-400 leading-relaxed">
          © 2025 Veersa Recruitment Portal
        </p>
      </div>
    </div>
  );
};

export default Landing;
