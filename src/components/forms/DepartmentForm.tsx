import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { createDepartment, updateDepartment, getUsers } from "../../services/api.js";

interface DepartmentFormProps {
  department?: any;
  onSubmit: (department: any) => void;
  onCancel: () => void;
}

export default function DepartmentForm({ department, onSubmit, onCancel }: DepartmentFormProps) {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    manager_id: undefined,
    team_member_ids: []
  });
  
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<any>({});

  // Fetch users for manager selection
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const userData = await getUsers();
        setUsers(userData);
      } catch (error) {
        console.error('Failed to fetch users:', error);
      }
    };
    
    fetchUsers();
  }, []);

  useEffect(() => {
    if (department) {
      setFormData({
        name: department.name || "",
        description: department.description || "",
        manager_id: department.manager_id ? department.manager_id.toString() : undefined,
        team_member_ids: department.team_members ? department.team_members.map((m: any) => m.id.toString()) : []
      });
    }
  }, [department]);

  const handleInputChange = (field: string, value: string | undefined) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors((prev: any) => ({
        ...prev,
        [field]: null
      }));
    }
  };

  const handleTeamMemberChange = (userId: string, checked: boolean) => {
    setFormData(prev => ({
      ...prev,
      team_member_ids: checked 
        ? [...prev.team_member_ids, userId]
        : prev.team_member_ids.filter((id: string) => id !== userId)
    }));
  };

  const validateForm = () => {
    const newErrors: any = {};
    
    if (!formData.name.trim()) newErrors.name = "Department name is required";
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setLoading(true);
    try {
      const submitData = {
        ...formData,
        manager_id: formData.manager_id ? parseInt(formData.manager_id) : null,
        team_member_ids: formData.team_member_ids.map((id: string) => parseInt(id))
      };

      let result;
      if (department?.id) {
        result = await updateDepartment(department.id, submitData);
        
        // First, clear all existing assignments for this department
        await fetch(`/api/departments/${department.id}/clear-members`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        
        // Then assign selected users to this department
        if (formData.team_member_ids.length > 0) {
          await Promise.all(
            formData.team_member_ids.map((userId: string) =>
              fetch(`/api/auth/users/${userId}`, {
                method: 'PUT',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify({ department_id: department.id })
              })
            )
          );
        }
      } else {
        result = await createDepartment(submitData);
        
        // For new departments, assign selected users
        if (result?.id && formData.team_member_ids.length > 0) {
          await Promise.all(
            formData.team_member_ids.map((userId: string) =>
              fetch(`/api/auth/users/${userId}`, {
                method: 'PUT',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify({ department_id: result.id })
              })
            )
          );
        }
      }
      
      onSubmit(result);
    } catch (error: any) {
      console.error('Failed to save department:', error);
      setErrors({ submit: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle>{department ? 'Edit Department' : 'Create New Department'}</DialogTitle>
      </DialogHeader>
      <Card className="w-full max-w-lg">
        <CardContent className="pt-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Department Name *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              className={errors.name ? 'border-red-500' : ''}
              placeholder="e.g. Software Development"
            />
            {errors.name && <p className="text-sm text-red-500">{errors.name}</p>}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              rows={3}
              placeholder="Enter department description..."
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="manager_id">Department Manager</Label>
            <Select 
              value={formData.manager_id ? formData.manager_id.toString() : "none"} 
              onValueChange={(value) => handleInputChange('manager_id', value === "none" ? undefined : value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select Manager (Optional)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No Manager</SelectItem>
                {users.filter((user: any) => user.role === 'hr_manager').map((user: any) => (
                  <SelectItem key={user.id} value={user.id.toString()}>
                    {user.first_name} {user.last_name} ({user.email})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Team Members</Label>
            <div className="max-h-40 overflow-y-auto border rounded-md p-3 space-y-2">
              {users.filter((user: any) => user.role === 'recruiter' || user.role === 'interviewer').length > 0 ? (
                users.filter((user: any) => user.role === 'recruiter' || user.role === 'interviewer').map((user: any) => (
                  <div key={user.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`user-${user.id}`}
                      checked={formData.team_member_ids.includes(user.id.toString())}
                      onCheckedChange={(checked) => handleTeamMemberChange(user.id.toString(), !!checked)}
                    />
                    <Label htmlFor={`user-${user.id}`} className="flex-1 cursor-pointer">
                      <div className="flex items-center justify-between">
                        <span>{user.first_name} {user.last_name}</span>
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded capitalize">
                          {user.role}
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground">{user.email}</div>
                    </Label>
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted-foreground">No recruiters or interviewers available</div>
              )}
            </div>
          </div>

          {errors.submit && (
            <div className="text-sm text-red-500 bg-red-50 p-3 rounded">
              {errors.submit}
            </div>
          )}

          <div className="flex justify-end space-x-2">
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving...' : (department ? 'Update' : 'Create')} Department
            </Button>
          </div>
        </form>
        </CardContent>
      </Card>
    </>
  );
}
