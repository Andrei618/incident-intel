import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
    return (
        <div className="flex flex-col items-center py-24 text-center gap-4">
            <h1 className="text-6xl font-bold">404</h1>
            <p className="text-xl text-muted-foreground">Page not found</p>
            <p className="text-sm text-muted-foreground">The page you're looking for doesn't exist.</p>
            <Button asChild className="mt-2">
               <Link to="/chat">Go to Chat</Link> 
            </Button>
            
        </div>
    )
}
