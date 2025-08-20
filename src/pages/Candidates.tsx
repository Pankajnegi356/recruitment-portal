import { useState, useEffect } from "react";
import { Plus, RefreshCw, List, Calendar, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getCandidates, getCandidateById } from "../services/api.js";
import { getStatusLabel, getStatusColor } from "../config/database.js";
import ProgressTracker from "@/components/ProgressTracker";


export default function Candidates() {
  const [viewMode, setViewMode] = useState<"list" | "timeline">("list");
  const [selectedCandidate, setSelectedCandidate] = useState<number | null>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [candidateDetails, setCandidateDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Fetch candidates on component mount
  useEffect(() => {
    const fetchCandidates = async () => {
      try {
        setLoading(true);
        const data = await getCandidates();
        setCandidates(data);
      } catch (error) {
        console.error('Failed to fetch candidates:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCandidates();
  }, []);

  // Fetch candidate details when selected
  useEffect(() => {
    const fetchCandidateDetails = async () => {
      if (selectedCandidate) {
        try {
          const details = await getCandidateById(selectedCandidate);
          setCandidateDetails(details);
        } catch (error) {
          console.error('Failed to fetch candidate details:', error);
        }
      }
    };

    fetchCandidateDetails();
  }, [selectedCandidate]);

  // Refresh data function
  const handleRefresh = async () => {
    try {
      setLoading(true);
      const data = await getCandidates();
      setCandidates(data);
    } catch (error) {
      console.error('Failed to refresh candidates:', error);
    } finally {
      setLoading(false);
    }
  };

  // Get avatar initials from name
  const getAvatarInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  // Handle status change for drag-and-drop
  const handleStatusChange = (candidateId: number, newStatus: number) => {
    setCandidates(prevCandidates => 
      prevCandidates.map(candidate => 
        candidate.id === candidateId 
          ? { ...candidate, status: newStatus } 
          : candidate
      )
    );
    console.log(`Candidate ${candidateId} status changed to ${newStatus}`);
  };

  // Handle candidate click from progress tracker
  const handleCandidateClick = (candidate: any) => {
    setSelectedCandidate(candidate.id);
  };

  // Candidate detail view
  if (selectedCandidate && candidateDetails) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center space-x-4">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => {
              setSelectedCandidate(null);
              setCandidateDetails(null);
            }}
            className="flex items-center space-x-2"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Candidates</span>
          </Button>
        </div>

        {/* Candidate Profile */}
        <div className="flex items-center space-x-4">
          <Avatar className="h-16 w-16">
            <AvatarFallback className="bg-green-600 text-white text-lg">
              {getAvatarInitials(candidateDetails.name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <h1 className="text-2xl font-bold text-foreground">{candidateDetails.name}</h1>
            <p className="text-muted-foreground">{getStatusLabel(candidateDetails.status)}</p>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="summary" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="summary">Summary</TabsTrigger>
            <TabsTrigger value="resume">Resume</TabsTrigger>
            <TabsTrigger value="status">Status</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
          
          <TabsContent value="summary" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Candidate Details */}
              <Card>
                <CardHeader>
                  <CardTitle>Candidate Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Full Name:</span>
                    <span className="text-muted-foreground">{candidateDetails.name}</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Email Address:</span>
                    <span className="text-muted-foreground">{candidateDetails.email}</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Phone Number:</span>
                    <span className="text-muted-foreground">{candidateDetails.phone || 'Not provided'}</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Applied For:</span>
                    <span className="text-muted-foreground">{candidateDetails.appliedFor}</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Skill Match Score:</span>
                    <span className="text-muted-foreground">{candidateDetails.skill_match_score}%</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Application Date:</span>
                    <span className="text-muted-foreground">{formatDate(candidateDetails.created_at)}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Candidate Summary */}
              <Card>
                <CardHeader>
                  <CardTitle>Candidate Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {candidateDetails.summary || 'No summary available.'}
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          <TabsContent value="resume" className="mt-6">
            <Card>
              <CardContent className="p-8">
                <div className="text-center">
                  <p className="text-muted-foreground">Resume content would be displayed here</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="status" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Current Status</CardTitle>
              </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center space-x-3">
                      <Badge className={getStatusColor(candidateDetails.status)}>
                        {getStatusLabel(candidateDetails.status)}
                      </Badge>
                      <span className="text-sm text-muted-foreground">Status Code: {candidateDetails.status}</span>
                    </div>
                    {candidateDetails.skill_match_score && (
                      <div className="flex items-center">
                        <span className="font-medium mr-2">Skill Match Score:</span>
                        <span className="text-muted-foreground">{candidateDetails.skill_match_score}% match</span>
                      </div>
                    )}
                  </div>
                </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="history" className="mt-6">
            <Card>
              <CardContent className="p-8">
                <div className="text-center">
                  <p className="text-muted-foreground">Application history would be displayed here</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Candidates</h1>
        <div className="flex items-center space-x-3">
          <div className="flex items-center border rounded-lg">
            <Button
              variant={viewMode === "list" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("list")}
              className="rounded-r-none"
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === "timeline" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("timeline")}
              className="rounded-l-none"
            >
              <Calendar className="h-4 w-4" />
            </Button>
          </div>
          <Button variant="outline" size="sm" className="flex items-center space-x-2" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Add Candidates Button */}
      <div>
        <Button className="flex items-center space-x-2">
          <Plus className="h-4 w-4" />
          <span>Add Candidates</span>
        </Button>
      </div>

      {viewMode === "list" ? (
        /* List View */
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead className="font-semibold text-table-header">Candidate Name</TableHead>
                  <TableHead className="font-semibold text-table-header">Applied for</TableHead>
                  <TableHead className="font-semibold text-table-header">Candidate Handler</TableHead>
                  <TableHead className="font-semibold text-table-header">Status</TableHead>
                  <TableHead className="font-semibold text-table-header">Applied date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {candidates.map((candidate) => (
                  <TableRow 
                    key={candidate.id} 
                    className="hover:bg-table-row-hover transition-colors cursor-pointer"
                    onClick={() => setSelectedCandidate(candidate.id)}
                  >
                    <TableCell className="font-medium text-primary hover:underline">
                      {candidate.name}
                    </TableCell>
                    <TableCell>{candidate.appliedFor}</TableCell>
                    <TableCell>{candidate.handler}</TableCell>
                    <TableCell>
                      <div className="inline-block">
                        <span 
                          className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-md ${getStatusColor(candidate.status)}`}
                          style={{ 
                            backgroundColor: candidate.status === 1 ? '#3b82f6' : candidate.status === 2 ? '#eab308' : '#6b7280',
                            color: 'white'
                          }}
                        >
                          {getStatusLabel(candidate.status)}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{formatDate(candidate.created_at || candidate.appliedDate)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        /* Progress Tracker View */
        loading ? (
          <div className="flex justify-center items-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin" />
            <span className="ml-2 text-muted-foreground">Loading candidates...</span>
          </div>
        ) : (
          <ProgressTracker 
            candidates={candidates}
            onCandidateClick={handleCandidateClick}
            onStatusChange={handleStatusChange}
          />
        )
      )}
    </div>
  );
}