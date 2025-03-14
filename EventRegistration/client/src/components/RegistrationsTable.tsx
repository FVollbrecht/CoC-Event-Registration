import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Edit, Trash2 } from "lucide-react";
import { useState } from "react";
import { Registration } from "@shared/schema";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { queryClient } from "@/lib/queryClient";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

interface RegistrationsTableProps {
  registrations: Registration[];
  onDeleteClick: (id: number) => void;
  onDelete: (id: number) => void;
}

const editFormSchema = z.object({
  count: z.coerce.number().min(1, {
    message: "Must have at least 1 participant.",
  }).max(18, {
    message: "Cannot exceed maximum of 18 participants per registration.",
  }),
});

export default function RegistrationsTable({ 
  registrations, 
  onDeleteClick,
  onDelete 
}: RegistrationsTableProps) {
  const [editingRegistration, setEditingRegistration] = useState<Registration | null>(null);
  const { toast } = useToast();
  
  const form = useForm<z.infer<typeof editFormSchema>>({
    resolver: zodResolver(editFormSchema),
    defaultValues: {
      count: 1,
    },
  });

  const handleEditClick = (registration: Registration) => {
    setEditingRegistration(registration);
    form.setValue("count", registration.count);
  };

  const handleEditSubmit = async (values: z.infer<typeof editFormSchema>) => {
    if (!editingRegistration) return;
    
    try {
      await apiRequest("PATCH", `/api/registrations/${editingRegistration.id}`, {
        count: values.count
      });
      
      // Update cache
      queryClient.invalidateQueries({ queryKey: ["/api/registrations"] });
      queryClient.invalidateQueries({ queryKey: ["/api/stats"] });
      queryClient.invalidateQueries({ queryKey: ["/api/activity"] });
      
      toast({
        title: "Registration updated",
        description: `Team "${editingRegistration.name}" has been updated to ${values.count} participants`,
      });
      
      setEditingRegistration(null);
    } catch (error: any) {
      const message = error.message || "An error occurred during update";
      
      toast({
        title: "Update failed",
        description: message,
        variant: "destructive",
      });
    }
  };

  if (registrations.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400">
        No registrations found. Add your first registration using the "Add Entry" button or the Discord command.
      </div>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
        <Table className="min-w-full rounded-lg overflow-hidden">
          <TableHeader className="bg-[#202225] border-b border-gray-700">
            <TableRow>
              <TableHead className="text-gray-400 uppercase">Team/Group</TableHead>
              <TableHead className="text-gray-400 uppercase">Participants</TableHead>
              <TableHead className="text-gray-400 uppercase">Registered By</TableHead>
              <TableHead className="text-gray-400 uppercase">Date</TableHead>
              <TableHead className="text-gray-400 uppercase text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-gray-700">
            {registrations.map((registration) => (
              <TableRow 
                key={registration.id} 
                className="bg-[#2f3136] hover:bg-[#40444b]"
              >
                <TableCell className="font-medium">
                  {registration.name}
                </TableCell>
                <TableCell>
                  {registration.count}
                </TableCell>
                <TableCell>
                  <div className="flex items-center">
                    <div className="h-8 w-8 rounded-full bg-[#5865F2] flex items-center justify-center mr-2">
                      <span className="text-xs">
                        {registration.discordUsername.slice(0, 2).toUpperCase()}
                      </span>
                    </div>
                    <span className="text-sm">{registration.discordUsername}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <div>{registration.registeredAt ? new Date(registration.registeredAt).toLocaleDateString() : 'N/A'}</div>
                  <div className="text-xs text-gray-400">
                    {registration.registeredAt ? new Date(registration.registeredAt).toLocaleTimeString() : 'N/A'}
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end space-x-2">
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      onClick={() => handleEditClick(registration)}
                      className="text-[#5865F2] hover:text-blue-400 hover:bg-transparent"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon"
                      onClick={() => onDeleteClick(registration.id)}
                      className="text-[#ED4245] hover:text-red-400 hover:bg-transparent"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Edit dialog */}
      <Dialog open={!!editingRegistration} onOpenChange={(open) => !open && setEditingRegistration(null)}>
        <DialogContent className="bg-[#36393f] text-white border-gray-700">
          <DialogHeader>
            <DialogTitle>Edit Registration</DialogTitle>
            <DialogDescription className="text-gray-400">
              Update the number of participants for {editingRegistration?.name}
            </DialogDescription>
          </DialogHeader>
          
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleEditSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="count"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Number of Participants</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
                        max={18}
                        {...field}
                        className="bg-[#2f3136] border-gray-600 text-white"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              <DialogFooter>
                <Button 
                  type="button" 
                  variant="secondary" 
                  onClick={() => setEditingRegistration(null)}
                  className="bg-gray-600 hover:bg-gray-700"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="bg-[#5865F2] hover:bg-opacity-80"
                >
                  Update
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </>
  );
}
