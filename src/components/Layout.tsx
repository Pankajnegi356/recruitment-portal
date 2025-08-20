import { useState, useEffect, useRef } from "react";
import { Search, Plus, HelpCircle, Bell, User, Menu, UserPlus, Briefcase, Calendar, MessageCircle, Settings, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getCandidates, getJobs } from "../services/api.js";
import { getStatusLabel } from "../config/database.js";
import { Sidebar } from "./Sidebar";

interface LayoutProps {
  children: React.ReactNode;
}


type SearchResult = {
  type: 'candidate' | 'job';
  id: number;
  title: string;
  subtitle: string;
  status: string;
};

export function Layout({ children }: LayoutProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [allCandidates, setAllCandidates] = useState<any[]>([]);
  const [allJobs, setAllJobs] = useState<any[]>([]);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  // Load data on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        /* 
         * DATABASE VERSION (Uncomment when ready):
         * const [candidates, jobs] = await Promise.all([
         *   getCandidates(),
         *   getJobs()
         * ]);
         * setAllCandidates(candidates);
         * setAllJobs(jobs);
         */
        
        // Using existing API functions that return mock data
        const [candidates, jobs] = await Promise.all([
          getCandidates(),
          getJobs()
        ]);
        setAllCandidates(candidates);
        setAllJobs(jobs);
      } catch (error) {
        console.error('Failed to load search data:', error);
      }
    };

    loadData();
  }, []);

  // Search functionality
  useEffect(() => {
    if (searchQuery.trim().length === 0) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    const query = searchQuery.toLowerCase();
    
    // Search candidates
    const candidateResults: SearchResult[] = allCandidates
      .filter(candidate => 
        candidate.name.toLowerCase().includes(query) ||
        candidate.appliedFor?.toLowerCase().includes(query) ||
        candidate.email.toLowerCase().includes(query)
      )
      .slice(0, 3)
      .map(candidate => ({
        type: 'candidate' as const,
        id: candidate.id,
        title: candidate.name,
        subtitle: candidate.appliedFor || 'No position specified',
        status: getStatusLabel(candidate.status) || 'Unknown',
      }));

    // Search jobs
    const jobResults: SearchResult[] = allJobs
      .filter(job => 
        job.title.toLowerCase().includes(query) ||
        job.department.toLowerCase().includes(query) ||
        job.team?.toLowerCase().includes(query)
      )
      .slice(0, 3)
      .map(job => ({
        type: 'job' as const,
        id: job.id,
        title: job.title,
        subtitle: `${job.department} • ${job.team}`,
        status: job.status,
      }));

    setSearchResults([...candidateResults, ...jobResults]);
    setShowResults(true);
    setSelectedIndex(-1);
  }, [searchQuery, allCandidates, allJobs]);

  // Handle click outside to close results
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showResults || searchResults.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => prev < searchResults.length - 1 ? prev + 1 : prev);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : prev);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleResultClick(searchResults[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowResults(false);
        setSelectedIndex(-1);
        break;
    }
  };

  const handleResultClick = (result: SearchResult) => {
    console.log('Navigate to:', result.type, result.id);
    // Here you would typically navigate to the specific candidate or job page
    setShowResults(false);
    setSearchQuery('');
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'applied':
        return 'bg-green-100 text-green-800';
      case 'shortlisted':
      case 'interview':
        return 'bg-yellow-100 text-yellow-800';
      case 'hired':
      case 'passed':
        return 'bg-blue-100 text-blue-800';
      case 'on hold':
        return 'bg-orange-100 text-orange-800';
      case 'completed':
      case 'canceled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <header className="fixed top-0 left-0 right-0 z-50 h-16 bg-nav-background border-b border-nav-border">
        <div className="flex items-center justify-between h-full px-6">
          {/* Left: Menu Toggle + Company/User Name */}
          <div className="flex items-center space-x-4">
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={toggleSidebar}
              className="hover:bg-muted"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="font-semibold text-lg text-foreground">
              Pankaj Negi
            </div>
          </div>

          {/* Center: Search Bar */}
          <div className="flex-1 max-w-lg mx-8" ref={searchRef}>
            <div className="relative group">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-muted-foreground h-5 w-5 transition-colors group-focus-within:text-primary" />
              <Input
                type="text"
                placeholder="Search candidates, jobs, or activities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => searchQuery && setShowResults(true)}
                className="pl-12 pr-4 py-2.5 bg-muted/50 border-0 rounded-full text-sm placeholder:text-muted-foreground focus-visible:bg-background focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:ring-offset-0 transition-all duration-200 hover:bg-muted/70"
              />
              {searchQuery && (
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setShowResults(false);
                  }}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}

              {/* Search Results Dropdown */}
              {showResults && searchResults.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-background border border-border rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
                  <div className="p-2">
                    {searchResults.map((result, index) => (
                      <div
                        key={`${result.type}-${result.id}`}
                        onClick={() => handleResultClick(result)}
                        className={`flex items-center justify-between p-3 rounded-md cursor-pointer transition-colors ${
                          index === selectedIndex ? 'bg-muted' : 'hover:bg-muted/50'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className="flex-shrink-0">
                            {result.type === 'candidate' ? (
                              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                <User className="h-4 w-4 text-blue-600" />
                              </div>
                            ) : (
                              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                                <Briefcase className="h-4 w-4 text-green-600" />
                              </div>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground truncate">
                              {result.title}
                            </p>
                            <p className="text-xs text-muted-foreground truncate">
                              {result.subtitle}
                            </p>
                          </div>
                        </div>
                        <Badge 
                          variant="secondary" 
                          className={`text-xs ${getStatusColor(result.status)}`}
                        >
                          {result.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                  
                  {searchResults.length === 0 && searchQuery && (
                    <div className="p-4 text-center text-muted-foreground text-sm">
                      No results found for "{searchQuery}"
                    </div>
                  )}
                  
                  <div className="border-t border-border p-2">
                    <div className="text-xs text-muted-foreground text-center">
                      Press <kbd className="px-1 py-0.5 bg-muted rounded text-xs">↑</kbd> <kbd className="px-1 py-0.5 bg-muted rounded text-xs">↓</kbd> to navigate, <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Enter</kbd> to select
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right: Action Buttons */}
          <div className="flex items-center space-x-3">
            {/* Create Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="hover:bg-muted">
                  <Plus className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>Create New</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="cursor-pointer">
                  <UserPlus className="mr-2 h-4 w-4" />
                  <span>Create Candidate</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="cursor-pointer">
                  <Briefcase className="mr-2 h-4 w-4" />
                  <span>Create Job</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="cursor-pointer">
                  <Calendar className="mr-2 h-4 w-4" />
                  <span>Create Activity</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Help Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="hover:bg-muted">
                  <HelpCircle className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-40">
                <DropdownMenuItem className="cursor-pointer">
                  <MessageCircle className="mr-2 h-4 w-4" />
                  <span>Talk to Us</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Notifications Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="hover:bg-muted relative">
                  <Bell className="h-6 w-6" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64">
                <DropdownMenuLabel>Notifications</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <div className="p-4 text-center text-muted-foreground">
                  No new notifications
                </div>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* User Profile Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-8 w-8 rounded-full p-0">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary text-primary-foreground">
                      P
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem className="cursor-pointer">
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="cursor-pointer text-destructive focus:text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Sign Out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <div className="flex pt-16">
        {/* Left Sidebar */}
        <Sidebar 
          isCollapsed={isSidebarCollapsed} 
          onExpandRequest={() => setIsSidebarCollapsed(false)}
        />
        
        {/* Main Content */}
        <main className={`flex-1 transition-all duration-300 ${isSidebarCollapsed ? 'ml-16' : 'ml-64'}`}>
          <div className="h-[calc(100vh-64px)] overflow-y-auto">
            <div className="p-6">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}