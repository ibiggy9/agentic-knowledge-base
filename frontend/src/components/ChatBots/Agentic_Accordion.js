import { motion } from "framer-motion";
import { Accordion, AccordionItem } from "@nextui-org/react";
import { useState, useEffect, useRef } from "react";
import { BiLoaderAlt } from "react-icons/bi"; 

const AgenticAccordion = ({ isMenuCollapsed, serverType, handleServerTypeChange, isLoading, isConnecting }) => {
  const [isOpen, setIsOpen] = useState(false);
  const accordionRef = useRef(null);
  
  const isProcessing = isLoading || isConnecting;

  const getSelectedSourceText = () => {
    if (serverType === "rfx") return "RFX";
    if (serverType === "raw_rfx") return "Raw RFX";
    return "Samsara";
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (accordionRef.current && !accordionRef.current.contains(event.target) && isOpen) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  return (
    <motion.div
      ref={accordionRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ type: 'spring', duration: 3 }}
      style={{
        position: "fixed",
        top: "10px",
        left: isMenuCollapsed ? "80px" : "310px",
        width: "225px",
        transition: "left 0.3s ease",
        zIndex: 50,
      }}
      className={isMenuCollapsed ? "block" : "hidden xl:block"}
    >
      <Accordion 
        disableAnimation={false}
        selectionMode="single"
        selectedKeys={isOpen ? ["competitive-intelligence"] : []}
        onSelectionChange={(keys) => setIsOpen(keys.size > 0)}
        className="focus:outline-none hover:bg-[#2F3136] bg-[#292C31] border border-[#363A3F] rounded-lg shadow-lg"
        itemClasses={{
          base: "focus:outline-none",
          title: "focus:outline-none",
          trigger: "focus:outline-none data-[hover=true]:bg-[#2F3136] p-2", 
          indicator: "text-indigo-300",
          content: "text-slate-300 text-xs"
        }}
      >
        <AccordionItem 
          key="competitive-intelligence" 
          className="text-slate-300 text-start text-sm hover:rounded-2xl transition-colors duration-200 focus:outline-none focus:ring-0" 
          aria-label="Agentic AI Platform Deep Research" 
          title={
            <span>
              Agentic <span className="bg-gradient-to-r from-violet-500 via-indigo-400 to-purple-500 text-transparent bg-clip-text font-bold">AI Platform Deep Research</span>
            </span>
          }
          subtitle={
            <span className="text-slate-300 text-xs">
              Current knowledge base: <span className="text-indigo-400">
                {getSelectedSourceText()}
                {isProcessing && <BiLoaderAlt className="inline ml-1 animate-spin" />}
              </span>
            </span>
          }
          hideIndicator={true}
        >
          <div className="p-2">
            <div className="flex flex-col gap-2">
              <button
                onClick={() => handleServerTypeChange("rfx")}
                className={`text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center justify-between ${
                  serverType === "rfx" 
                    ? "bg-indigo-500 text-white" 
                    : "bg-[#36393F] text-slate-300 hover:text-slate-50 hover:bg-[#2F3136]"
                } ${isProcessing ? "opacity-70 cursor-not-allowed" : ""}`}
                disabled={isProcessing}
              >
                <span>RFX Database</span>
                {isProcessing && serverType === "rfx" && 
                  <BiLoaderAlt className="animate-spin ml-2" />
                }
              </button>
              <button
                onClick={() => handleServerTypeChange("raw_rfx")}
                className={`text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center justify-between ${
                  serverType === "raw_rfx" 
                    ? "bg-indigo-500 text-white" 
                    : "bg-[#36393F] text-slate-300 hover:text-slate-50 hover:bg-[#2F3136]"
                } ${isProcessing ? "opacity-70 cursor-not-allowed" : ""}`}
                disabled={isProcessing}
              >
                <span>Raw RFX</span>
                {isProcessing && serverType === "raw_rfx" && 
                  <BiLoaderAlt className="animate-spin ml-2" />
                }
              </button>
              <button
                onClick={() => handleServerTypeChange("samsara")}
                className={`text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center justify-between ${
                  serverType === "samsara" 
                    ? "bg-indigo-500 text-white" 
                    : "bg-[#36393F] text-slate-300 hover:text-slate-50 hover:bg-[#2F3136]"
                } ${isProcessing ? "opacity-70 cursor-not-allowed" : ""}`}
                disabled={isProcessing}
              >
                <span>Samsara Analysis</span>
                {isProcessing && serverType === "samsara" && 
                  <BiLoaderAlt className="animate-spin ml-2" />
                }
              </button>
            </div>
            <p className="text-slate-300 text-xs mt-2">
              {serverType === "rfx" 
                ? "Access and analyze RFX database with SQL queries" 
                : serverType === "raw_rfx"
                  ? "Access raw RFX 2025 content and documentation"
                  : "Analyze Samsara documents from Google Drive"}
            </p>
            <p className="text-slate-300 text-xs mt-2">
              Any questions contact: <a className="text-indigo-400 hover:text-indigo-300 underline" href="mailto:contact@example.com">contact@example.com</a>
            </p>
          </div>
        </AccordionItem>
      </Accordion>
    </motion.div>
  );
};

export default AgenticAccordion;