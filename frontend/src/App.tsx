import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Index from "./pages/Index.tsx";
import NotFound from "./pages/NotFound.tsx";
import { AppLayout } from "./components/layout/AppLayout";
import Dashboard from "./pages/app/Dashboard";
import RuleSearch from "./pages/app/RuleSearch";
import Sources from "./pages/app/Sources";
import ReviewQueue from "./pages/app/ReviewQueue";
import Workflows from "./pages/app/Workflows";
import Analytics from "./pages/app/Analytics";
import Admin from "./pages/app/Admin";
import SubmissionValidator from "./pages/app/SubmissionValidator";
import Outcomes from "./pages/app/Outcomes";
import SubmissionPath from "./pages/app/SubmissionPath";
import WorkflowRunner from "./pages/app/WorkflowRunner";
import Rejections from "./pages/app/Rejections";
import Onboarding from "./pages/app/Onboarding";
import DemoGuide from "./pages/app/DemoGuide";
import WebhooksPage from "./pages/app/Webhooks";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="search" element={<RuleSearch />} />
            <Route path="sources" element={<Sources />} />
            <Route path="review" element={<ReviewQueue />} />
            <Route path="workflows" element={<Workflows />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="validate" element={<SubmissionValidator />} />
            <Route path="outcomes" element={<Outcomes />} />
            <Route path="submission" element={<SubmissionPath />} />
            <Route path="workflow-runner" element={<WorkflowRunner />} />
            <Route path="rejections" element={<Rejections />} />
            <Route path="onboarding" element={<Onboarding />} />
            <Route path="demo" element={<DemoGuide />} />
            <Route path="webhooks" element={<WebhooksPage />} />
            <Route path="admin" element={<Admin />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
