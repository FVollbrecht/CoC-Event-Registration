import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { apiRequest } from "@/lib/queryClient";
import { queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  deleteId: number | null;
}

export default function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  deleteId,
}: ConfirmationModalProps) {
  const { toast } = useToast();

  const handleDelete = async () => {
    if (!deleteId) return;
    
    try {
      await apiRequest("DELETE", `/api/registrations/${deleteId}`);
      
      // Update cache
      queryClient.invalidateQueries({ queryKey: ["/api/registrations"] });
      queryClient.invalidateQueries({ queryKey: ["/api/stats"] });
      queryClient.invalidateQueries({ queryKey: ["/api/activity"] });
      
      toast({
        title: "Registration deleted",
        description: "The registration has been successfully deleted",
      });
      
      onConfirm();
    } catch (error) {
      toast({
        title: "Delete failed",
        description: "There was an error deleting the registration",
        variant: "destructive",
      });
      onClose();
    }
  };

  return (
    <AlertDialog open={isOpen} onOpenChange={onClose}>
      <AlertDialogContent className="bg-[#36393f] text-white border-gray-700">
        <AlertDialogHeader>
          <AlertDialogTitle>Confirm Action</AlertDialogTitle>
          <AlertDialogDescription className="text-gray-300">
            Are you sure you want to remove this registration? This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className="bg-gray-600 hover:bg-gray-700 text-white">Cancel</AlertDialogCancel>
          <AlertDialogAction 
            className="bg-[#ED4245] hover:bg-opacity-80"
            onClick={handleDelete}
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
