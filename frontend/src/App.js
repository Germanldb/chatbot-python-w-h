import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import './App.css';
import './index.css';
import { WhatsAppConnection } from './components/WhatsAppConnection';
import { Dashboard } from './components/Dashboard';
import { ChatPanel } from './components/ChatPanel';
import { Button } from './components/ui/button';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Smartphone, 
  Menu,
  X
} from 'lucide-react';

function Navigation() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/chat', label: 'Conversaciones', icon: MessageSquare },
    { path: '/whatsapp', label: 'WhatsApp', icon: Smartphone },
  ];

  return (
    <div className="bg-primary text-primary-foreground">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-accent rounded-lg flex items-center justify-center">
              <Smartphone className="w-6 h-6 text-accent-foreground" />
            </div>
            <span className="text-xl font-heading font-bold hidden md:block">
              Fashion Assistant
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
                    isActive
                      ? 'bg-primary-foreground/10 text-primary-foreground'
                      : 'text-primary-foreground/70 hover:text-primary-foreground hover:bg-primary-foreground/5'
                  }`}
                  data-testid={`nav-${item.label.toLowerCase()}`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 rounded-md hover:bg-primary-foreground/10"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            data-testid="mobile-menu-button"
          >
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="md:hidden py-4 space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`flex items-center space-x-2 px-4 py-3 rounded-md transition-colors ${
                    isActive
                      ? 'bg-primary-foreground/10 text-primary-foreground'
                      : 'text-primary-foreground/70 hover:text-primary-foreground hover:bg-primary-foreground/5'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <div className="App min-h-screen bg-background">
      <BrowserRouter>
        <Navigation />
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<ChatPanel />} />
            <Route path="/whatsapp" element={<WhatsAppConnection />} />
          </Routes>
        </main>
      </BrowserRouter>
    </div>
  );
}

export default App;