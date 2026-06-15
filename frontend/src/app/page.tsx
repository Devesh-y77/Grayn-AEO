"use client";

import React, { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import AnalyzeStep from "../components/steps/AnalyzeStep";
import ConfirmSetupStep, { SetupData } from "../components/steps/ConfirmSetupStep";
import ReviewPromptsStep, { PromptData } from "../components/steps/ReviewPromptsStep";
import QueryingModal from "../components/steps/QueryingModal";
import DashboardStep from "../components/steps/DashboardStep";

// Configured local storage keys
const LOCAL_STORAGE_KEY = "grayn_aeo_config";

type StepState = "ANALYZING" | "CONFIRM_SETUP" | "REVIEW_PROMPTS" | "QUERYING" | "DASHBOARD";

export default function Page() {
  const [step, setStep] = useState<StepState>("ANALYZING");
  const [setupData, setSetupData] = useState<SetupData>({
    domain: "",
    brandName: "iScape",
    location: "Arlington Heights, IL",
    languages: ["english"],
    competitors: [
      { name: "PRO Landscape", url: "", description: "Both target landscape professionals and homeowners with photo-based visualization, 3D/2D design tools, and client proposal generation for outdoor space planning." },
      { name: "DynaSCAPE", url: "", description: "Both serve professional landscapers and contractors with cloud-based landscape design, estimating, and business management tools for creating client-ready proposals." },
      { name: "VizTerra", url: "", description: "Both target landscape design professionals with advanced 3D visualization and augmented reality tools for presenting outdoor living space concepts to clients." },
      { name: "Realtime Landscaping", url: "", description: "Both target homeowners and landscape professionals seeking realistic 3D visualization and detailed design tools for planning outdoor spaces before construction." },
      { name: "Planner 5D", url: "", description: "Both target homeowners seeking intuitive mobile and web-based tools to visually plan and design outdoor spaces with drag-and-drop elements." }
    ],
    attributes: ["pricing", "comparison", "enterprise", "resource", "implementation"],
    searchTopics: [
      "best landscape design app for contractors with client proposals",
      "augmented reality landscape design app for homeowners",
      "landscape design software with 3D visualization and plant library"
    ],
    promptsPerTopic: 5
  });

  const [reportData, setReportData] = useState<any>(null);
  const [config, setConfig] = useState<any>(null);

  useEffect(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (typeof window !== "undefined" && window.location.hostname !== "localhost" && parsed.backendUrl.includes("localhost")) {
          parsed.backendUrl = parsed.backendUrl.replace("localhost", window.location.hostname);
          localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(parsed));
        }
        parsed.apiKey = "gk_devprefix_devsecretkey123456789";
        setConfig(parsed);
      } catch (e) {
      }
    }
  }, []);

  const getApiUrl = (path: string) => {
    if (typeof window !== "undefined" && window.location.hostname.includes("vercel.app")) {
      return `https://grayn-aeo-production.up.railway.app${path}`;
    }
    let base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return `${base}${path}`;
  };

  const fetchReport = async () => {
    if (!config) return;
    try {
      const headers = {
        "Authorization": `Bearer ${config.apiKey}`,
        "Content-Type": "application/json",
      };
      const res = await fetch(getApiUrl("/v1/report"), { headers, cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setReportData(data);
        if (data && data.workspace) {
          setSetupData(prev => ({
            ...prev,
            domain: data.workspace.domain,
            brandName: data.workspace.brand_name
          }));
        }
      }
    } catch (e) {
      console.error("Failed to fetch report", e);
    }
  };

  // Skip wizard if we already have report data and they refresh (optional, but requested to show flow)
  useEffect(() => {
    if (config) {
      fetchReport();
    }
  }, [config]);

  return (
    <div className="flex h-screen w-full bg-[#0a0a0a] overflow-hidden font-sans">
      <Sidebar workspaceName={setupData.brandName} />
      
      <main className="flex-1 relative overflow-hidden flex flex-col">
        {step === "ANALYZING" && (
          <AnalyzeStep 
            domain={setupData.domain} 
            setDomain={(d) => setSetupData({...setupData, domain: d})} 
            onComplete={() => setStep("CONFIRM_SETUP")} 
          />
        )}
        
        {step === "CONFIRM_SETUP" && (
          <ConfirmSetupStep 
            initialData={setupData} 
            onComplete={(data) => {
              setSetupData(data);
              setStep("REVIEW_PROMPTS");
            }} 
            onTryDifferentUrl={() => setStep("ANALYZING")}
          />
        )}

        {step === "REVIEW_PROMPTS" && (
          <ReviewPromptsStep 
            setupData={setupData} 
            onRunPrompts={(prompts) => {
              setStep("QUERYING");
            }} 
          />
        )}

        {step === "QUERYING" && (
          <>
            <DashboardStep reportData={reportData} setupData={setupData} />
            <QueryingModal 
              onComplete={() => {
                setStep("DASHBOARD");
              }} 
            />
          </>
        )}

        {step === "DASHBOARD" && (
          <DashboardStep reportData={reportData} setupData={setupData} />
        )}

      </main>
    </div>
  );
}
