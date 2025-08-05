'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link';
import { BiMessageDetail } from "react-icons/bi"
import { RiMenuFoldLine, RiMenuUnfoldLine } from "react-icons/ri"
import Image from 'next/image'
import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'
import { Tooltip } from "@nextui-org/tooltip"
import { AiOutlinePlus } from "react-icons/ai"
import TestingStuff from '../ChatBots/TestingStuff'
import { MdDashboard } from "react-icons/md"

export default function Menu({ onCollapse, onReset }) {
  const currentPath = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(true);
  const [showExpandButton, setShowExpandButton] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  
  useEffect(() => {
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [currentPath]);

  useEffect(() => {
    onCollapse?.(isCollapsed);
  }, [isCollapsed, onCollapse]);
  
  function handleResize() {
    setIsMobile(window.innerWidth <= 768);
    setShowExpandButton(window.innerWidth > 768);
  }
  
  function handleNewChat() {
    if (onReset) {
      onReset();
    }
    window.location.reload();
  }
  
  const BrandLogo = ({ isCollapsed }) => (
    <>
      <motion.div
        animate={{ 
          width: isCollapsed ? "65px" : "250px",
          height: isCollapsed ? "65px" : "250px",
          marginBottom: isCollapsed ? "8px" : "0px",
          marginTop: isCollapsed ? "8px" : "0px"
        }}
        transition={{ duration: 0.3, ease: "linear" }}
        className="relative rounded-full w-full flex justify-center"
      >
        <TestingStuff />
      </motion.div>

      {!isCollapsed && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2, delay: 0.1 }}
        >
          <div className='text-white text-center pb-4 mt-4 text-lg font-bold'>
            Agentic <span className="bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500 text-transparent bg-clip-text">AI Platform</span>
          </div>
          <div className='text-[#B9BBBE] w-full pb-3 text-center italic text-sm'>Intelligent Knowledge Synthesis</div>
        </motion.div>
      )}
    </>
  );

  const MenuButton = ({ onClick, children, label, className }) => (
    <button 
      onClick={onClick} 
      className={`flex flex-row items-center w-full px-4 py-4 hover:bg-[#4F545C] rounded-2xl mb-2 ${className}`}
    >
      {children}
      <div className='text-white text-sm'>{label}</div>
    </button>
  );

  const MenuLink = ({ href, onClick, children, label, className, isActive }) => (
    <Link 
      href={href} 
      onClick={onClick} 
      className={`flex flex-row items-center w-full px-4 py-4 hover:bg-[#4F545C] rounded-2xl mb-2 ${isActive && 'bg-[#36393F]'} ${className}`}
    >
      {children}
      <div className='text-white text-sm'>{label}</div>
    </Link>
  );

  const MobileMenu = ({ isMenuOpen, setIsMenuOpen, currentPath, handleNewChat }) => (
    <AnimatePresence>
      {!isMenuOpen && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease: "linear" }}
          onClick={() => setIsMenuOpen(true)}
          className="fixed top-4 left-4 z-50 p-2 text-white hover:bg-[#4F545C] rounded-full"
        >
          <RiMenuUnfoldLine size={24} />
        </motion.button>
      )}

      {isMenuOpen && (
        <motion.div
          initial={{ x: "-100%" }}
          animate={{ x: 0 }}
          exit={{ x: "-100%" }}
          transition={{ duration: 0.3, ease: "linear" }}
          className="fixed inset-0 z-40 flex flex-col"
          style={{ 
            backgroundImage: "linear-gradient(to bottom, #2C2F33, #292B2F)"
          }}
        >
          <div className="flex justify-end p-4">
            <button
              onClick={() => setIsMenuOpen(false)}
              className="p-2 text-white hover:bg-[#4F545C] rounded-full"
            >
              <RiMenuFoldLine size={24} />
            </button>
          </div>

          <div className="flex flex-col items-center p-4">
            <div className="relative">
              <Image
                alt="Company Logo"
                src="/assets/logo.png"
                width={150}
                height={150}
                className="rounded-2xl"
              />  
            </div>
            <div className='text-white text-center pb-4 text-lg font-bold'>
              Agentic <span className="bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500 text-transparent bg-clip-text">AI Platform</span>
            </div>
            <div className="text-[#B9BBBE] w-full pb-3 text-center italic text-sm">Intelligent Knowledge Synthesis</div>

            <MenuButton 
              onClick={() => {
                setIsMenuOpen(false);
                handleNewChat();
              }}
              className="mb-2"
              label="Start New Chat"
            >
              <AiOutlinePlus size={20} color='white' className='mr-3' />
            </MenuButton>

            <MenuLink 
              href="/admin" 
              onClick={() => setIsMenuOpen(false)} 
              isActive={currentPath === '/admin'}
              label="Admin Dashboard"
            >
              <MdDashboard size={20} color='white' className='mr-3' />
            </MenuLink>

            <a 
              href="mailto:contact@example.com" 
              onClick={() => setIsMenuOpen(false)} 
              className="flex flex-row items-center w-full px-4 py-4 hover:bg-[#4F545C] rounded-2xl mb-2"
            >
              <BiMessageDetail size={20} color='white' className='mr-3' />
              <div className='text-white text-sm'>Get in Touch</div>
            </a>
          </div>

          <div className="mt-auto p-4 text-center">
            <p className='text-[#B9BBBE] text-xs'>This AI platform can make mistakes, so double check results.</p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  const DesktopMenu = ({ isCollapsed, setIsCollapsed, showExpandButton, handleNewChat }) => (
    <motion.div 
      initial={{ width: "75px" }}
      animate={{ width: isCollapsed ? "75px" : "300px" }}
      transition={{ duration: 0.3, ease: "linear" }}
      className='h-screen flex flex-col justify-between border-r border-[#2D2F32]'
      style={{ 
        backgroundImage: "linear-gradient(to bottom, #2C2F33, #292B2F)"
      }}
    >
      <div className='flex flex-col items-center p-1'>
        {showExpandButton && (
          <CollapseButton isCollapsed={isCollapsed} onClick={() => setIsCollapsed(!isCollapsed)} />
        )}

        <BrandLogo isCollapsed={isCollapsed} />

        {isCollapsed ? (
          <Tooltip 
            content="Start New Chat" 
            placement="right"
            classNames={{
              content: "bg-[#18191C] rounded-xl text-white border-[#36393F] py-1 px-2"
            }}
          >
            <button 
              onClick={handleNewChat} 
              className="flex flex-row items-center justify-center mb-1 w-full px-4 py-4 hover:bg-[#36393F] rounded-2xl"
            >
              <AiOutlinePlus size={20} color='white' />
            </button>
          </Tooltip>
        ) : (
          <button 
            onClick={handleNewChat} 
            className="flex flex-row items-center mb-1 w-full px-4 py-4 hover:bg-[#36393F] rounded-2xl"
          >
            <AiOutlinePlus size={20} color='white' className='mr-3' />
            <div className='text-white text-sm'>Start New Chat</div>
          </button>
        )}

        <ContactLink isCollapsed={isCollapsed} />
      </div>
      
      {!isCollapsed && (
        <div className="flex-col justify-center items-center text-[#B9BBBE] text-xs p-4">
          <p>This AI platform can make mistakes, so double check results.</p>
        </div>
      )}
    </motion.div>
  );

  const CollapseButton = ({ isCollapsed, onClick }) => (
    <Tooltip 
      classNames={{
        content: "bg-[#18191C] text-white border-[#36393F] py-1 px-2"
      }}
    >
      <button 
        onClick={onClick}
        className={`p-2 text-[#B9BBBE] hover:bg-[#4F545C] hover:text-white rounded-full ${isCollapsed ? 'self-center' : 'self-end'}`}
      >
        {isCollapsed ? <RiMenuUnfoldLine size={20} /> : <RiMenuFoldLine size={20} />}
      </button>
    </Tooltip>
  );

  const ContactLink = ({ isCollapsed }) => (
    isCollapsed ? (
      <Tooltip 
        content="Get in Touch" 
        placement="right"
        classNames={{
          content: "bg-[#18191C] rounded-xl text-white border-[#36393F] py-1 px-2"
        }}
      >
        <a 
          href="mailto:contact@example.com" 
          className="flex flex-row items-center justify-center mb-1 w-full px-4 py-4 hover:bg-[#36393F] rounded-2xl"
        >
          <BiMessageDetail size={20} color='white' />
        </a>
      </Tooltip>
    ) : (
      <a 
        href="mailto:contact@example.com" 
        className="flex flex-row items-center mb-1 w-full px-4 py-4 hover:bg-[#36393F] rounded-2xl"
      >
        <BiMessageDetail size={20} color='white' className='mr-3' />
        <div className='text-white text-sm'>Get in Touch</div>
      </a>
    )
  );

  return isMobile 
    ? <MobileMenu 
        isMenuOpen={isMenuOpen}
        setIsMenuOpen={setIsMenuOpen}
        currentPath={currentPath}
        handleNewChat={handleNewChat}
      />
    : <DesktopMenu 
        isCollapsed={isCollapsed}
        setIsCollapsed={setIsCollapsed}
        showExpandButton={showExpandButton}
        handleNewChat={handleNewChat}
      />;
}