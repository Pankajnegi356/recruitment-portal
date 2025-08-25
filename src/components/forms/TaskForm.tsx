import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { createActivityLog, updateActivityLog, getUsers } from "../../services/api.js";

interface TaskFormProps {
  activity?: any;
  onSubmit: (activity: any) => void;
  onCancel: () => void;
}

export default function TaskForm({ activity, onSubmit, onCancel }: TaskFormProps) {
  const [formData, setFormData] = useState({
    user_id: "",
    action: "",
    entity_type: "candidate",
    entity_id: "",
    details: ""
  });
  
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  // Fetch users for user selection
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
    if (activity) {
      setFormData({
        user_id: activity.user_id?.toString() || "",
        action: activity.action || "",
        entity_type: activity.entity_type || "candidate",
        entity_id: activity.entity_id?.toString() || "",
        details: activity.details || ""
      });
    }
  }, [activity]);

  // For backward compatibility
  const task = activity;

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.user_id || !formData.user_id.trim()) newErrors.user_id = "User is required";
    if (!formData.action.trim()) newErrors.action = "Action is required";
    if (!formData.entity_id.trim()) newErrors.entity_id = "Entity ID is required";
    
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
        user_id: parseInt(formData.user_id),
        entity_id: parseInt(formData.entity_id),
      };

      let result;
      if (activity?.id) {
        result = await updateActivityLog(activity.id, submitData);
      } else {
        result = await createActivityLog(submitData);
      }
      
      onSubmit(result);
    } catch (error) {
      console.error('Failed to save activity:', error);
      setErrors({ submit: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle>{task ? 'Edit Activity Log' : 'Create New Activity Log'}</DialogTitle>
      </DialogHeader>
      <Card className="w-full max-w-3xl">
        <CardContent className="pt-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="user_id">User *</Label>
              <Select value={formData.user_id} onValueChange={(value) => handleInputChange('user_id', value)}>
                <SelectTrigger className={errors.user_id ? 'border-red-500' : ''}>
                  <SelectValue placeholder="Select User" />
                </SelectTrigger>
                <SelectContent>
                  {users.map((user) => (
                    <SelectItem key={user.id} value={user.id.toString()}>
                      {user.first_name} {user.last_name} ({user.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.user_id && <p className="text-sm text-red-500">{errors.user_id}</p>}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="entity_type">Entity Type</Label>
              <Select value={formData.entity_type} onValueChange={(value) => handleInputChange('entity_type', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select Entity Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="candidate">Candidate</SelectItem>
                  <SelectItem value="job">Job</SelectItem>
                  <SelectItem value="department">Department</SelectItem>
                  <SelectItem value="interview">Interview</SelectItem>
                  <SelectItem value="application">Application</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="action">Action *</Label>
            <Input
              id="action"
              value={formData.action}
              onChange={(e) => handleInputChange('action', e.target.value)}
              className={errors.action ? 'border-red-500' : ''}
              placeholder="e.g. created, updated, deleted, viewed..."
            />
            {errors.action && <p className="text-sm text-red-500">{errors.action}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="entity_id">Entity ID *</Label>
            <Input
              id="entity_id"
              type="number"
              value={formData.entity_id}
              onChange={(e) => handleInputChange('entity_id', e.target.value)}
              className={errors.entity_id ? 'border-red-500' : ''}
              placeholder="Enter entity ID (candidate ID, job ID, etc.)..."
            />
            {errors.entity_id && <p className="text-sm text-red-500">{errors.entity_id}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="details">Details (Optional)</Label>
            <Textarea
              id="details"
              value={formData.details}
              onChange={(e) => handleInputChange('details', e.target.value)}
              rows={3}
              placeholder="Enter additional details about this activity..."
            />
          </div>

          {errors.submit && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{errors.submit}</p>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading}
            >
              {loading ? 'Saving...' : task ? 'Update Activity' : 'Create Activity'}
            </Button>
          </div>
        </form>
        </CardContent>
      </Card>
    </>
  );
}
