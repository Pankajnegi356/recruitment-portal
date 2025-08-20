import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
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

interface CandidateCardProps {
  candidate: Candidate;
  onClick?: () => void;
  onDragStart?: () => void;
  onDragEnd?: () => void;
  isDragging?: boolean;
  statusColor?: string;
}

export default function CandidateCard({
  candidate,
  onClick,
  onDragStart,
  onDragEnd,
  isDragging = false,
  statusColor
}: CandidateCardProps) {
  // Get avatar initials from name
  const getAvatarInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  // Get avatar color based on initials
  const getAvatarColor = (initials: string) => {
    const colors = [
      'bg-blue-500',
      'bg-purple-500', 
      'bg-green-500',
      'bg-orange-500',
      'bg-pink-500',
      'bg-indigo-500'
    ];
    const index = initials.charCodeAt(0) % colors.length;
    return colors[index];
  };

  const initials = getAvatarInitials(candidate.name);
  const avatarColor = getAvatarColor(initials);

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    console.log('Edit candidate:', candidate.id);
  };

  return (
    <Card 
      className={`cursor-move hover:shadow-sm transition-all duration-200 border border-gray-200 bg-white ${
        isDragging ? 'opacity-50 rotate-3' : 'hover:shadow-md'
      }`}
      draggable
      onDragStart={(e) => {
        onDragStart?.();
      }}
      onDragEnd={(e) => {
        onDragEnd?.();
      }}
    >
      <CardContent className="p-3">
        <div className="flex items-start justify-between mb-2">
          <Badge 
            className={`text-xs px-2 py-1 rounded-full font-medium ${statusColor || 'bg-blue-500 text-white'}`}
          >
            {candidate.status === 1 ? 'Applied' : 
             candidate.status === 2 ? 'Shortlisted' :
             candidate.status === 3 ? 'Pre Screening' :
             candidate.status === 4 ? 'Technical Interview' : 'Unknown'}
          </Badge>
          
          <div className="flex items-center space-x-2">
            {candidate.skill_match_score && (
              <span className="text-xs text-gray-500 font-medium">
                {candidate.skill_match_score}% match
              </span>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-6 w-6 p-0 hover:bg-gray-100"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreVertical className="h-4 w-4 text-gray-400" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-32">
                <DropdownMenuItem onClick={handleEdit} className="text-sm">
                  <Edit2 className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <Avatar className="h-10 w-10 flex-shrink-0">
            <AvatarFallback className={`${avatarColor} text-white text-sm font-bold`}>
              {initials}
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-gray-900 truncate mb-1">
              {candidate.name}
            </h4>
            <p className="text-xs text-gray-500 truncate">
              {candidate.email}
            </p>
          </div>
        </div>
        
        <div className="mt-3 pt-2 border-t border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Applied for:</p>
          <p className="text-sm font-medium text-gray-800 truncate">
            {candidate.appliedFor}
          </p>
        </div>
        
        <div className="mt-2">
          <p className="text-xs text-gray-400">
            Applied: {new Date(candidate.created_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric'
            })}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
