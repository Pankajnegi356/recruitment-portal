import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreVertical, Edit2 } from "lucide-react";

interface Candidate {
  id: number;
  name: string;
  email: string;
  phone?: string;
  appliedFor: string;
  status: number;
  created_at: string;
  skill_match_score?: number;
}

interface ProgressTrackerProps {
  candidates: Candidate[];
  onCandidateClick?: (candidate: Candidate) => void;
  onStatusChange?: (candidateId: number, newStatus: number) => void;
}

const PROGRESS_STAGES = [
  { id: 1, title: "New Candidates", status: 1, color: "bg-blue-100" },
  { id: 2, title: "Shortlisted", status: 2, color: "bg-yellow-100" },
  { id: 3, title: "Pre Screening Test", status: 3, color: "bg-orange-100" },
  { id: 4, title: "Technical Interview", status: 4, color: "bg-purple-100" }
];

function SimpleCandidateCard({ candidate, onEdit }: { candidate: Candidate; onEdit: () => void }) {
  const getAvatarInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  const getAvatarColor = (initials: string) => {
    const colors = [
      'bg-blue-500', 'bg-purple-500', 'bg-green-500',
      'bg-orange-500', 'bg-pink-500', 'bg-indigo-500'
    ];
    const index = initials.charCodeAt(0) % colors.length;
    return colors[index];
  };

  const initials = getAvatarInitials(candidate.name);
  const avatarColor = getAvatarColor(initials);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3 flex-1">
          <Avatar className="h-10 w-10">
            <AvatarFallback className={`${avatarColor} text-white text-sm font-bold`}>
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-gray-900 truncate">
              {candidate.name}
            </h4>
            <p className="text-xs text-gray-500 truncate">
              {candidate.email}
            </p>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onEdit}>
              <Edit2 className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

export default function ProgressTracker({
  candidates,
  onCandidateClick,
  onStatusChange
}: ProgressTrackerProps) {
  const getCandidatesByStatus = (status: number) => {
    return candidates.filter(candidate => candidate.status === status);
  };

  const handleEdit = (candidate: Candidate) => {
    console.log('Edit candidate:', candidate.id);
  };

  return (
    <div className="bg-gray-50 p-6 rounded-lg">
      {/* Progress Header */}
      <div className="flex items-center mb-6">
        {PROGRESS_STAGES.map((stage, index) => {
          const count = getCandidatesByStatus(stage.status).length;

          return (
            <div key={stage.id} className="flex items-center">
              {/* Stage Box */}
              <div className="flex items-center justify-center bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm" style={{ width: '200px' }}>
                <span className="text-sm font-medium text-gray-700 mr-2 text-center">
                  {stage.title}
                </span>
                {count > 0 && (
                  <Badge variant="secondary" className="bg-blue-500 text-white text-xs px-2 py-1">
                    {count}
                  </Badge>
                )}
              </div>
              
              {/* Triangle Arrow */}
              {index < PROGRESS_STAGES.length - 1 && (
                <div className="flex items-center mx-2">
                  <div className="w-0 h-0 border-l-[12px] border-l-white border-t-[12px] border-t-transparent border-b-[12px] border-b-transparent"></div>
                  <div className="w-4 h-0.5 bg-gray-300"></div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Candidates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {PROGRESS_STAGES.map((stage) => {
          const stageCandidates = getCandidatesByStatus(stage.status);
          
          return (
            <div key={stage.id} className={`${stage.color} rounded-lg p-4`}>
              <div className="space-y-3">
                {stageCandidates.length === 0 ? (
                  <p className="text-center text-gray-500 text-sm py-8">No candidates</p>
                ) : (
                  stageCandidates.map((candidate) => (
                    <SimpleCandidateCard
                      key={candidate.id}
                      candidate={candidate}
                      onEdit={() => handleEdit(candidate)}
                    />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
