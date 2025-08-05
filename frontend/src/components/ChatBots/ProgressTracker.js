import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, Circle, Clock, AlertCircle } from 'lucide-react'

function PhaseIndicator({ phase, currentPhase, index }) {
  const isActive = phase.id === currentPhase;
  const isCompleted = phases.findIndex(p => p.id === currentPhase) > index;
  
  return (
    <motion.div 
      key={phase.id} 
      className="flex-1 flex flex-col items-center relative z-10"
      initial={{ scale: 0, opacity: 0.5 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.3, delay: 0.1 + (index * 0.1) }}
    >
      <motion.div 
        className="w-8 h-8 rounded-full flex items-center justify-center mb-2"
        initial={false}
        animate={{ 
          backgroundColor: isActive ? '#4F46E5' : isCompleted ? '#059669' : '#4F545C',
          color: isActive || isCompleted ? '#FFFFFF' : '#B9BBBE'
        }}
        transition={{ duration: 0.5, ease: "easeInOut" }}
      >
        <motion.div
          initial={false}
          animate={{ 
            opacity: isCompleted ? 1 : 0,
            scale: isCompleted ? 1 : 0,
            position: 'absolute'
          }}
          transition={{ duration: 0.3 }}
        >
          <CheckCircle size={16} />
        </motion.div>
        
        <motion.div
          initial={false}
          animate={{ 
            opacity: isActive ? 1 : 0,
            scale: isActive ? 1 : 0,
            position: 'absolute'
          }}
          transition={{ opacity: { duration: 0.3 }, scale: { duration: 0.3 } }}
        >
          {isActive ? (
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 3, repeat: Infinity, ease: "linear" }}>
              <Clock size={16} className="text-indigo-500" />
            </motion.div>
          ) : isCompleted ? (
            <CheckCircle size={16} className="text-green-500" />
          ) : (
            <Circle size={16} className="text-[#4F545C]" />
          )}
        </motion.div>
        
        <motion.div
          initial={false}
          animate={{ 
            opacity: (!isActive && !isCompleted) ? 1 : 0,
            scale: (!isActive && !isCompleted) ? 1 : 0,
            position: 'absolute'
          }}
          transition={{ duration: 0.3 }}
        >
          <Circle size={16} />
        </motion.div>
      </motion.div>
      
      <motion.div 
        className="text-xs font-medium"
        initial={false}
        animate={{ color: isActive || isCompleted ? '#FFFFFF' : '#B9BBBE' }}
        transition={{ duration: 0.5 }}
      >
        {phase.label}
      </motion.div>
      
      <motion.div 
        className="text-xs text-[#B9BBBE] mt-1 max-w-[120px] text-center"
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: isActive ? 'auto' : 0, opacity: isActive ? 1 : 0 }}
        transition={{ duration: 0.3 }}
      >
        {phase.description}
      </motion.div>
    </motion.div>
  );
};

function PlanStep({ step, executionSteps, currentStep }) {
  const execStep = executionSteps.find(es => es.step === step.number);
  const isActive = currentStep === step.number || execStep?.status === 'in-progress';
  const isCompleted = execStep?.status === 'completed';
  
  return (
    <motion.div 
      initial={{ opacity: 0.5 }}
      animate={{ 
        opacity: 1,
        backgroundColor: isActive ? 'rgba(67, 56, 202, 0.1)' 
                      : isCompleted ? 'rgba(16, 185, 129, 0.1)' 
                      : 'transparent'
      }}
      transition={{ duration: 0.3, backgroundColor: { duration: 0.8 } }}
      key={`step-${step.number}-${isCompleted ? 'completed' : isActive ? 'active' : 'pending'}`}
      className="flex items-start p-2 rounded"
    >
      <div className="flex-shrink-0 mr-3 mt-0.5">
        {isCompleted ? (
          <motion.div initial={{ scale: 0.5 }} animate={{ scale: 1 }} transition={{ duration: 0.4 }}>
            <CheckCircle size={16} className="text-green-500" />
          </motion.div>
        ) : isActive ? (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          >
            <Clock size={16} className="text-indigo-500" />
          </motion.div>
        ) : (
          <Circle size={16} className="text-[#4F545C]" />
        )}
      </div>
      <div className="flex-1">
        <div className={`text-sm ${isCompleted ? 'text-[#DCDDDE]' : isActive ? 'text-indigo-300' : 'text-[#B9BBBE]'}`}>
          <span className="font-medium">{step.number}. </span>
          {formatStepDescription(step.description)}
          {step.description.includes("get_file_content") && 
            <p className="text-white text-xs font-italic font-bold animate-pulse">
              NOTE: If your query is broad and requires many files to be read, this can take several minutes.
            </p>
          }
        </div>
        
        {isActive && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="text-xs text-[#B9BBBE] mt-1"
          >
            {execStep?.metrics ? (
              <div className="flex flex-wrap gap-1">
                {Object.entries(execStep.metrics).map(([key, value]) => (
                  <span key={key} className="bg-[#292b2f] px-2 py-0.5 rounded">
                    {key.replace('_', ' ')}: <b>{value}</b>
                  </span>
                ))}
              </div>
            ) : (
              <div className="animate-pulse">Accessing data...</div>
            )}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

const MetricsDisplay = ({ metrics }) => (
  <div className="grid grid-cols-3 gap-2">
    <div className="bg-[#2F3136] p-2 rounded">
      <div className="text-xs text-[#B9BBBE]">Queries</div>
      <div className="text-lg font-bold text-indigo-400">
        {metrics.queries_executed || 0}
      </div>
    </div>
    <div className="bg-[#2F3136] p-2 rounded">
      <div className="text-xs text-[#B9BBBE]">Documents</div>
      <div className="text-lg font-bold text-purple-400">
        {metrics.documents_processed || 0}
      </div>
    </div>
    <div className="bg-[#2F3136] p-2 rounded">
      <div className="text-xs text-[#B9BBBE]">Total</div>
      <div className="text-lg font-bold text-blue-400">
        {(metrics.queries_executed || 0) + (metrics.documents_processed || 0)}
      </div>
    </div>
  </div>
);

const phases = [
  { id: 'analyzing', label: 'Analyzing Request', description: 'Determining query intent' },
  { id: 'planning', label: 'Planning Analysis', description: 'Developing step-by-step strategy' },
  { id: 'executing', label: 'Executing Plan', description: 'Gathering and processing data' },
  { id: 'synthesizing', label: 'Synthesizing Results', description: 'Creating comprehensive response' },
];

function formatStepDescription(description) {
  const toolPattern = /^Use the \w+(?:_\w+)*(?: again)? to\s+(.*)/i;
  const match = description.match(toolPattern);
  
  if (match) {
    const remainingText = match[1];
    return remainingText.charAt(0).toUpperCase() + remainingText.substring(1);
  }
  
  return description;
};

function extractStepFromMessage(message) {
  const lowerMessage = message.toLowerCase();
  if (!lowerMessage.includes('executing step') && !lowerMessage.includes('step')) {
    return { stepNum: null, totalSteps: null };
  }
  
  const words = message.split(' ');
  
  for (let i = 0; i < words.length; i++) {
    if (words[i].includes('/')) {
      const parts = words[i].split('/');
      if (parts.length === 2) {
        const num = parseInt(parts[0], 10);
        const total = parseInt(parts[1], 10);
        
        if (!isNaN(num) && !isNaN(total)) {
          return { stepNum: num, totalSteps: total };
        }
      }
    } else if (lowerMessage.includes('step') && !isNaN(parseInt(words[i], 10))) {
      const possibleStepNum = parseInt(words[i], 10);
      if (!isNaN(possibleStepNum)) {
        return { stepNum: possibleStepNum, totalSteps: null };
      }
    }
  }
  
  return { stepNum: null, totalSteps: null };
};

function extractCompletedStep(message) {
  if (!message.includes("Successfully") || !message.includes("step")) {
    return null;
  }
  
  const completedMatch = message.match(/step (\d+)/i);
  if (!completedMatch) return null;
  
  const completedStep = parseInt(completedMatch[1], 10);
  return isNaN(completedStep) ? null : completedStep;
};

function extractPlanSteps(planText) {
  if (planText.includes("FULL PLAN:")) {
    const fullPlan = planText.split("FULL PLAN:")[1].trim();
    const stepsByNumber = fullPlan.match(/\d+\.\s+[^\n]+/g);
    
    if (stepsByNumber && stepsByNumber.length > 0) {
      return stepsByNumber.map(step => {
        const match = step.match(/(\d+)\.\s+(.*)/);
        return {
          number: parseInt(match[1], 10),
          description: match[2].trim()
        };
      });
    }
  }
  
  const steps = [];
  const lines = planText.split('\n');
  
  function checkStepByStepSection() {
    let stepSection = false;
    for (const line of lines) {
      if (line.includes("Step-by-Step Plan")) {
        stepSection = true;
        continue;
      }
      
      if (stepSection) {
        const stepMatch = line.match(/^\s*(\d+)\.\s+(.*)/);
        if (stepMatch) {
          steps.push({
            number: parseInt(stepMatch[1], 10),
            description: stepMatch[2].trim()
          });
        }
      }
    }
  };
  
  function checkBoldSections() {
    if (planText.includes("Step-by-Step Plan")) {
      for (let i = 0; i < lines.length; i++) {
        const stepMatch = lines[i].match(/^\s*(\d+)\.\s+\*\*(.*?):\*\*/);
        if (stepMatch) {
          steps.push({
            number: parseInt(stepMatch[1], 10),
            description: stepMatch[2].trim()
          });
        }
      }
    }
  };
  
  checkStepByStepSection();
  
  if (steps.length === 0) {
    checkBoldSections();
  }
  
  return steps;
};

export function ProgressTracker({ 
  isVisible, 
  progressIndicator, 
  progressDetails, 
  serverType,
  onPlanLoaded
}) {
  const [plan, setPlan] = useState([]);
  const [currentPhase, setCurrentPhase] = useState('analyzing');
  const [executionSteps, setExecutionSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [analysisPlan, setAnalysisPlan] = useState(null);
  const [isContentLoaded, setIsContentLoaded] = useState(false);
  const [operationMetrics, setOperationMetrics] = useState({
    queries_executed: 0,
    documents_processed: 0,
    folders_scanned: 0
  });

  useEffect(() => {
    if (!progressDetails || progressDetails.length === 0) return;
    
    progressDetails.forEach(processProgressMessage);
    
    if (plan.length > 0 && executionSteps.length === 0) {
      const initialSteps = plan.map(step => ({
        step: step.number,
        description: step.description,
        status: 'pending',
        total: plan.length
      }));
      setExecutionSteps(initialSteps);
    }
  }, [progressDetails, plan.length]);

  useEffect(() => {
    if (plan.length > 0 && onPlanLoaded && typeof onPlanLoaded === 'function') {
      setTimeout(onPlanLoaded, 100);
    }
  }, [plan.length, onPlanLoaded]);

  const markStepAsCompleted = stepNumber => {
    setExecutionSteps(prev => {
      if (prev.some(s => s.step === stepNumber && s.status === 'completed')) {
        return prev;
      }
      
      return prev.map(s => 
        s.step === stepNumber ? { ...s, status: 'completed' } : s
      );
    });
  };

  function processProgressMessage(detail) {
    const message = detail.message || "";
    const metrics = detail.metrics || {};
    
    if (message.includes("Analyzing your request") || message.includes("Thinking...")) {
      setCurrentPhase('analyzing');
    } 
    else if (message.includes("Phase 1") || message.includes("Developing analysis strategy")) {
      setCurrentPhase('planning');
    }
    else if (message.includes("Phase 2") || message.includes("Executing") || message.match(/Step \d+\/\d+/)) {
      setCurrentPhase('executing');
    }
    else if (message.includes("Phase 3") || message.includes("Synthesizing")) {
      setCurrentPhase('synthesizing');
    }
    
    if (message.includes("## Analysis Strategy") || message.includes("Analysis Strategy and Step-by-Step Plan") || message.includes("FULL PLAN:")) {
      setAnalysisPlan(message);
      
      const planSteps = extractPlanSteps(message);
      if (planSteps.length > 0) {
        setPlan(planSteps);
      }
    }
    
    const { stepNum, totalSteps } = extractStepFromMessage(message);
    
    if (stepNum !== null) {
      setCurrentStep(stepNum);
      
      setExecutionSteps(prev => {
        if (prev.some(s => s.step === stepNum)) return prev;
        
        const finalTotalSteps = totalSteps || plan.length;
        
        let stepDescription = plan.find(s => s.number === stepNum)?.description;
        
        if (!stepDescription && message.includes(':')) {
          stepDescription = message.split(':')[1].trim();
          
          if (stepDescription.startsWith('Use the') && stepDescription.includes(' to ')) {
            const parts = stepDescription.split(' to ');
            if (parts.length >= 2) {
              let processedDesc = parts[1];
              processedDesc = processedDesc.charAt(0).toUpperCase() + processedDesc.slice(1);
              stepDescription = processedDesc;
            }
          }
        }
        
        return [...prev, {
          step: stepNum,
          description: stepDescription || `Step ${stepNum}`,
          status: 'in-progress',
          total: finalTotalSteps
        }];
      });
    }
    
    const completedStep = extractCompletedStep(message);
    if (completedStep) {
      markStepAsCompleted(completedStep);
    }
    
    if (detail.details && detail.details.status === "completed" && detail.details.step) {
      markStepAsCompleted(parseInt(detail.details.step, 10));
    }
    
    const status = detail.details?.status;
    const stepNumber = detail.details?.step;
    if (status && stepNumber) {
      setExecutionSteps(prev => prev.map(s => 
        s.step === stepNumber 
          ? (s.status === 'completed' ? s : { ...s, status: status })
          : s
      ));
    }
    
    if (metrics && Object.keys(metrics).length > 0 && currentStep > 0) {
      setExecutionSteps(prev => prev.map(s => 
        s.step === currentStep ? { ...s, metrics: metrics } : s
      ));
    }

    if (detail.details?.metrics) {
      setOperationMetrics(prev => ({
        ...prev,
        ...detail.details.metrics
      }));
    }
  };

  

  if (!isVisible) return null;
  
  return (
    <AnimatePresence>
      <motion.div 
        className="relative z-0"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="relative">
          <div 
            className="absolute rounded-lg bg-gradient-to-r from-indigo-600 via-purple-500 to-pink-500"
            style={{ 
              filter: 'blur(2px)',
              backgroundSize: '200% 200%',
              animation: 'moveGradient 3s ease infinite',
              top: -1.5,
              left: -1.5,
              bottom: -1.5,
              right: -1.5,
              width: 'calc(100% - 0.75rem + 1.5px)',
              zIndex: 0,
              position: 'absolute',
              height: 'auto',
              inset: '-1.5px',
              pointerEvents: 'none'
            }}
          ></div>
          <motion.div 
            initial={{ y: 50 }}
            animate={{ y: 0 }}
            transition={{ duration: 0.4 }}
            className="relative bg-[#36393F] rounded-lg p-4 shadow-lg z-1"
            style={{
              margin: '1.5px',
              marginBottom: '1.5rem',
              marginRight: '0.75rem',
            }}
          >
            <h3 className="text-white font-semibold border-b border-[#40444B] pb-2 mb-3">
              Processing Your Request
            </h3>
            
            <div className="flex items-center mb-6 relative">
              <div className="absolute h-1 bg-[#40444B] left-7 right-7 top-1/2 transform -translate-y-1/2 z-0"></div>
              {phases.map((phase, index) => (
                <PhaseIndicator 
                  key={phase.id}
                  phase={phase} 
                  currentPhase={currentPhase} 
                  index={index} 
                />
              ))}
            </div>
            
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0 mr-3">
                <motion.div
                  animate={{ 
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 1, 0.7]
                  }}
                  transition={{ 
                    duration: 1.5, 
                    repeat: Infinity,
                    repeatType: "reverse" 
                  }}
                  className="w-3 h-3 rounded-full bg-indigo-500"
                />
              </div>
              <div className="text-[#DCDDDE] text-sm font-bold">
                {progressIndicator || "Processing..."}
              </div>
            </div>
            
            {(currentPhase === 'executing' || currentPhase === 'synthesizing') && plan.length > 0 && (
              <div className="mt-4 border-t border-[#40444B] pt-3">
                <h4 className="text-[#DCDDDE] font-medium mb-2 text-sm">Execution Plan:</h4>
                <div className="space-y-2">
                  {plan.map(step => (
                    <PlanStep 
                      key={step.number}
                      step={step} 
                      executionSteps={executionSteps} 
                      currentStep={currentStep}
                    />
                  ))}
                </div>
              </div>
            )}
            
            <div className="mt-4 text-xs text-center text-[#B9BBBE]">
              {serverType === "rfx" 
                ? "Analyzing database for insights and patterns..." 
                : "Processing and extracting information from documents..."}
            </div>

            {serverType !== "rfx" && (
              <div className="mt-4 border-t border-[#40444B] pt-3">
                <h4 className="text-[#DCDDDE] font-medium mb-2 text-sm">Operations Performed:</h4>
                <MetricsDisplay metrics={operationMetrics} />
              </div>
            )}
          </motion.div>
        </div>
        
        <style jsx>{`
          @keyframes moveGradient {
            0% {
              background-position: 0% 50%;
            }
            50% {
              background-position: 100% 50%;
            }
            100% {
              background-position: 0% 50%;
            }
          }
        `}</style>
      </motion.div>
    </AnimatePresence>
  );
};

  