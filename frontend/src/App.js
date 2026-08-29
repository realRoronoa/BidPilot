import "@/App.css";
import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import AppShell from "@/components/layout/AppShell";
import { PageLoader } from "@/components/common";

import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Portfolio from "@/pages/Portfolio";
import Opportunities from "@/pages/Opportunities";
import Capacity from "@/pages/Capacity";
import Analyses from "@/pages/Analyses";
import NewAnalysis from "@/pages/NewAnalysis";
import AnalysisWorkspace from "@/pages/AnalysisWorkspace";
import EvidenceViewer from "@/pages/EvidenceViewer";
import Company from "@/pages/Company";
import Documents from "@/pages/Documents";
import Notifications from "@/pages/Notifications";
import Settings from "@/pages/Settings";
import Users from "@/pages/Users";
import Billing from "@/pages/Billing";

function Protected({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  if (user === null) return <PageLoader label="Authenticating" />;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return <AppShell>{children}</AppShell>;
}

function PublicOnly({ children }) {
  const { user } = useAuth();
  if (user === null) return <PageLoader label="Loading" />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
      <Route path="/portfolio" element={<Protected><Portfolio /></Protected>} />
      <Route path="/opportunities" element={<Protected><Opportunities /></Protected>} />
      <Route path="/capacity" element={<Protected><Capacity /></Protected>} />
      <Route path="/analyses" element={<Protected><Analyses /></Protected>} />
      <Route path="/analyses/new" element={<Protected><NewAnalysis /></Protected>} />
      <Route path="/analyses/:id/evidence/:eid" element={<Protected><EvidenceViewer /></Protected>} />
      <Route path="/analyses/:id" element={<Protected><AnalysisWorkspace /></Protected>} />
      <Route path="/analyses/:id/:tab" element={<Protected><AnalysisWorkspace /></Protected>} />
      <Route path="/company" element={<Protected><Company /></Protected>} />
      <Route path="/documents" element={<Protected><Documents /></Protected>} />
      <Route path="/notifications" element={<Protected><Notifications /></Protected>} />
      <Route path="/users" element={<Protected><Users /></Protected>} />
      <Route path="/billing" element={<Protected><Billing /></Protected>} />
      <Route path="/settings" element={<Protected><Settings /></Protected>} />
      <Route path="/settings/:section" element={<Protected><Settings /></Protected>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </BrowserRouter>
  );
}
