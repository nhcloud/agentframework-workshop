import React, { useState, useEffect, useRef } from 'react';
import styled, { createGlobalStyle, ThemeProvider } from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import Select from 'react-select';
import ReactMarkdown from 'react-markdown';
import { 
  Send, 
  Mic, 
  MicOff, 
  Volume2, 
  Play, 
  Pause, 
  Square,
  RotateCcw,
  Users,
  Trash2,
  Bot,
  ChevronLeft,
  ChevronRight,
  Menu,
  AlertCircle,
  Image as ImageIcon,
  Plus,
  X,
  Shield,
  Upload,
  FileText
} from 'lucide-react';

import ChatService from './services/ChatService';
import VoiceService from './services/VoiceService';
import SafetyTester from './SafetyTester';
import ToolsSelector from './components/ToolsSelector';

// Global styles
const GlobalStyle = createGlobalStyle`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
    background: #f0f2f5;
    height: 100vh;
    overflow: hidden;
  }

  #root {
    height: 100vh;
  }
`;

// Theme - Professional Corporate Design
const theme = {
  colors: {
    primary: '#2563eb',
    primaryDark: '#1d4ed8',
    primaryLight: '#3b82f6',
    secondary: '#0891b2',
    background: '#ffffff',
    backgroundAlt: '#f8fafc',
    surface: '#ffffff',
    surfaceHover: '#f1f5f9',
    text: '#0f172a',
    textSecondary: '#475569',
    textMuted: '#94a3b8',
    border: '#e2e8f0',
    borderLight: '#f1f5f9',
    accent: '#0891b2',
    success: '#059669',
    warning: '#d97706',
    error: '#dc2626',
    voiceActive: '#dc2626',
    voiceInactive: '#6b7280',
    professional: '#1e40af',
    professionalDark: '#1e3a8a'
  },
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)'
  },
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    full: '9999px'
  }
};

// Styled components
const AppContainer = styled.div`
  display: flex;
  height: 100vh;
  background: ${props => props.theme.colors.backgroundAlt};
`;

const Sidebar = styled(motion.div)`
  width: ${props => props.collapsed ? '0px' : '320px'};
  background: ${props => props.theme.colors.surface};
  border-right: ${props => props.collapsed ? 'none' : `1px solid ${props.theme.colors.border}`};
  display: flex;
  flex-direction: column;
  box-shadow: ${props => props.collapsed ? 'none' : props.theme.shadows.lg};
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
`;

const SidebarContent = styled.div`
  width: 320px;
  display: flex;
  flex-direction: column;
  opacity: ${props => props.collapsed ? 0 : 1};
  transition: opacity 0.2s ease;
  pointer-events: ${props => props.collapsed ? 'none' : 'auto'};
  overflow-y: auto;
  max-height: calc(100vh - 100px);
  
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: ${props => props.theme.colors.border};
    border-radius: 3px;
    
    &:hover {
      background: ${props => props.theme.colors.textMuted};
    }
  }
`;

const SidebarToggle = styled(motion.button)`
  position: absolute;
  right: ${props => props.collapsed ? '-40px' : '-20px'};
  top: 20px;
  width: 40px;
  height: 40px;
  border-radius: ${props => props.theme.borderRadius.full};
  background: ${props => props.theme.colors.surface};
  border: 1px solid ${props => props.theme.colors.border};
  color: ${props => props.theme.colors.text};
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: ${props => props.theme.shadows.md};
  transition: all 0.3s ease;
  z-index: 10;

  &:hover {
    background: ${props => props.theme.colors.primary};
    color: white;
    transform: scale(1.05);
  }

  &:active {
    transform: scale(0.95);
  }
`;

const SidebarHeader = styled.div`
  padding: 24px;
  border-bottom: 1px solid ${props => props.theme.colors.borderLight};
  background: linear-gradient(135deg, ${props => props.theme.colors.professional} 0%, ${props => props.theme.colors.professionalDark} 100%);
  color: white;

  h1 {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  p {
    opacity: 0.9;
    font-size: 14px;
  }
`;

const AgentSection = styled.div`
  padding: 20px;
  border-bottom: 1px solid ${props => props.theme.colors.borderLight};

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: ${props => props.theme.colors.text};
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
`;

const MaxTurnsControl = styled.div`
  margin-top: 12px;
  padding: 12px;
  background: ${props => props.theme.colors.backgroundAlt};
  border-radius: ${props => props.theme.borderRadius.md};
  border: 1px solid ${props => props.theme.colors.border};

  label {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 14px;
    font-weight: 500;
    color: ${props => props.theme.colors.text};
    margin-bottom: 8px;
  }

  input[type="number"] {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid ${props => props.theme.colors.border};
    border-radius: ${props => props.theme.borderRadius.sm};
    font-size: 14px;
    color: ${props => props.theme.colors.text};
    background: ${props => props.theme.colors.surface};
    transition: all 0.2s ease;

    &:focus {
      outline: none;
      border-color: ${props => props.theme.colors.primary};
      box-shadow: 0 0 0 3px ${props => props.theme.colors.primary}20;
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      background: ${props => props.theme.colors.borderLight};
    }
  }

  .help-text {
    font-size: 11px;
    color: ${props => props.theme.colors.textSecondary};
    margin-top: 6px;
    line-height: 1.4;
  }
`;

const FormatSelector = styled.div`
  margin-top: 12px;
  padding: 12px;
  background: ${props => props.theme.colors.backgroundAlt};
  border-radius: ${props => props.theme.borderRadius.md};
  border: 1px solid ${props => props.theme.colors.border};

  label {
    display: block;
    font-size: 14px;
    font-weight: 500;
    color: ${props => props.theme.colors.text};
    margin-bottom: 8px;
  }

  .format-options {
    display: flex;
    gap: 8px;
  }

  .format-option {
    flex: 1;
    padding: 10px 12px;
    border: 2px solid ${props => props.theme.colors.border};
    border-radius: ${props => props.theme.borderRadius.sm};
    background: ${props => props.theme.colors.surface};
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: center;

    &:hover {
      border-color: ${props => props.theme.colors.primary};
      background: ${props => props.theme.colors.primaryLight}10;
    }

    &.active {
      border-color: ${props => props.theme.colors.primary};
      background: ${props => props.theme.colors.primary}15;
      color: ${props => props.theme.colors.primary};
      font-weight: 600;
    }

    .format-title {
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 4px;
    }

    .format-description {
      font-size: 10px;
      color: ${props => props.theme.colors.textMuted};
      line-height: 1.3;
    }
  }

  .help-text {
    font-size: 11px;
    color: ${props => props.theme.colors.textSecondary};
    margin-top: 8px;
    line-height: 1.4;
  }
`;

const ErrorMessage = styled.div`
  padding: 12px;
  background: ${props => props.theme.colors.error}15;
  border: 1px solid ${props => props.theme.colors.error};
  border-radius: ${props => props.theme.borderRadius.md};
  color: ${props => props.theme.colors.error};
  font-size: 13px;
  line-height: 1.5;
  margin-top: 12px;
  display: flex;
  align-items: flex-start;
  gap: 8px;

  svg {
    flex-shrink: 0;
    margin-top: 2px;
  }

  .error-content {
    flex: 1;
  }

  .error-title {
    font-weight: 600;
    margin-bottom: 4px;
  }

  .error-details {
    font-size: 12px;
    opacity: 0.9;
  }
`;

const VoiceSection = styled.div`
  padding: 20px;
  border-bottom: 1px solid ${props => props.theme.colors.borderLight};

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: ${props => props.theme.colors.text};
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
`;

const VoiceControls = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const VoiceToggle = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: ${props => props.theme.colors.backgroundAlt};
  border-radius: ${props => props.theme.borderRadius.md};
  border: 1px solid ${props => props.theme.colors.border};

  span {
    font-size: 14px;
    font-weight: 500;
    color: ${props => props.theme.colors.text};
  }
`;

const ToggleSwitch = styled(motion.button)`
  width: 52px;
  height: 28px;
  border-radius: 14px;
  background: ${props => props.active ? props.theme.colors.primary : '#cbd5e1'};
  border: 1px solid ${props => props.active ? props.theme.colors.primaryDark : '#94a3b8'};
  cursor: pointer;
  position: relative;
  transition: all 0.3s ease;
  box-shadow: ${props => props.active ? 'inset 0 1px 3px rgba(0,0,0,0.2)' : 'inset 0 1px 2px rgba(0,0,0,0.1)'};

  &:hover {
    background: ${props => props.active ? props.theme.colors.primaryDark : '#94a3b8'};
  }

  &::after {
    content: '';
    position: absolute;
    top: 2px;
    left: ${props => props.active ? '26px' : '2px'};
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: white;
    transition: all 0.3s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  }
`;

const VoicePlaybackControls = styled.div`
  display: flex;
  gap: 12px;
  padding: 12px;
  background: ${props => props.enabled ? props.theme.colors.backgroundAlt : props.theme.colors.backgroundAlt};
  border-radius: ${props => props.theme.borderRadius.lg};
  border: 1px solid ${props => props.enabled ? props.theme.colors.border : props.theme.colors.borderLight};
  opacity: ${props => props.enabled ? 1 : 0.6};
  transition: all 0.3s ease;
`;

const VoiceButton = styled(motion.button)`
  width: 40px;
  height: 40px;
  border: 2px solid ${props => props.active ? props.theme.colors.primary : props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.full};
  background: ${props => props.active ? props.theme.colors.primary : props.theme.colors.surface};
  color: ${props => props.active ? 'white' : props.theme.colors.text};
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: ${props => props.active ? props.theme.shadows.md : props.theme.shadows.sm};

  &:hover {
    background: ${props => props.active ? props.theme.colors.primaryDark : props.theme.colors.primary};
    color: white;
    border-color: ${props => props.theme.colors.primary};
    transform: none;
    box-shadow: ${props => props.theme.shadows.lg};
  }

  &:active {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
    &:hover {
      background: ${props => props.theme.colors.surface};
      color: ${props => props.theme.colors.textMuted};
      border-color: ${props => props.theme.colors.border};
    }
  }
`;

const MainContent = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  background: ${props => props.theme.colors.background};
  transition: all 0.3s ease;
`;

const ChatHeader = styled.div`
  padding: 16px 24px;
  border-bottom: 1px solid ${props => props.theme.colors.borderLight};
  background: ${props => props.theme.colors.surface};
  display: flex;
  align-items: center;
  justify-content: space-between;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.95);

  h2 {
    font-size: 18px;
    font-weight: 600;
    color: ${props => props.theme.colors.text};
    display: flex;
    align-items: center;
    gap: 10px;
    letter-spacing: -0.02em;
  }
`;

const MenuButton = styled(motion.button)`
  width: 36px;
  height: 36px;
  border-radius: ${props => props.theme.borderRadius.md};
  background: transparent;
  border: 1px solid ${props => props.theme.colors.border};
  color: ${props => props.theme.colors.text};
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-right: 12px;

  &:hover {
    background: ${props => props.theme.colors.backgroundAlt};
    border-color: ${props => props.theme.colors.primary};
    color: ${props => props.theme.colors.primary};
  }

  &:active {
    transform: scale(0.95);
  }
`;

const ChatActions = styled.div`
  display: flex;
  gap: 8px;
`;

const ActionButton = styled(motion.button)`
  padding: 8px 16px;
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.md};
  background: ${props => props.theme.colors.surface};
  color: ${props => props.theme.colors.textSecondary};
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 0.5px;

  &:hover {
    background: ${props => props.theme.colors.surfaceHover};
    transform: translateY(-1px);
  }
`;

const ChatMessages = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: ${props => props.theme.colors.backgroundAlt};

  &::-webkit-scrollbar {
    width: 10px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
    border-radius: 5px;
  }

  &::-webkit-scrollbar-thumb {
    background: ${props => props.theme.colors.border};
    border-radius: 5px;
    border: 2px solid ${props => props.theme.colors.backgroundAlt};

    &:hover {
      background: ${props => props.theme.colors.textMuted};
    }
  }
`;

const Message = styled(motion.div)`
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: ${props => props.isUser ? '80%' : '100%'};
  margin-left: ${props => props.isUser ? 'auto' : '0'};
  flex-direction: ${props => props.isUser ? 'row-reverse' : 'row'};
`;

const MessageAvatar = styled.div`
  width: 36px;
  height: 36px;
  border-radius: ${props => props.theme.borderRadius.full};
  background: ${props => props.isUser 
    ? `linear-gradient(135deg, ${props.theme.colors.primary} 0%, ${props.theme.colors.primaryDark} 100%)`
    : `linear-gradient(135deg, ${props.theme.colors.professional} 0%, ${props.theme.colors.professionalDark} 100%)`
  };
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
`;

const MessageContent = styled.div`
  background: ${props => props.isUser 
    ? `linear-gradient(135deg, ${props.theme.colors.primary} 0%, ${props.theme.colors.primaryDark} 100%)`
    : props.theme.colors.surface
  };
  color: ${props => props.isUser ? 'white' : props.theme.colors.text};
  padding: 14px 18px;
  border-radius: ${props => props.isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px'};
  box-shadow: ${props => props.isUser 
    ? '0 2px 12px rgba(37, 99, 235, 0.3)'
    : '0 2px 12px rgba(0, 0, 0, 0.08)'
  };
  border: ${props => props.isUser ? 'none' : `1px solid ${props.theme.colors.borderLight}`};
  max-width: 100%;
  word-wrap: break-word;
  line-height: 1.6;
  font-size: 15px;

  /* Markdown styling */
  h1, h2, h3, h4, h5, h6 {
    margin-top: 16px;
    margin-bottom: 8px;
    font-weight: 600;
    line-height: 1.3;
  }

  h1 { font-size: 1.5em; }
  h2 { font-size: 1.3em; }
  h3 { font-size: 1.1em; }

  p {
    margin: 8px 0;
  }

  ul, ol {
    margin: 8px 0;
    padding-left: 24px;
  }

  li {
    margin: 4px 0;
  }

  strong {
    font-weight: 600;
  }

  code {
    background: ${props => props.isUser ? 'rgba(255,255,255,0.2)' : props.theme.colors.backgroundAlt};
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
    font-family: 'Courier New', monospace;
  }

  pre {
    background: ${props => props.isUser ? 'rgba(255,255,255,0.1)' : props.theme.colors.backgroundAlt};
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;

    code {
      background: none;
      padding: 0;
    }
  }

  .message-meta {
    margin-top: 10px;
    font-size: 11px;
    opacity: ${props => props.isUser ? 0.85 : 0.6};
    display: flex;
    align-items: center;
    gap: 12px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;

    .turn-badge {
      background: ${props => props.theme.colors.primary}30;
      color: ${props => props.isUser ? 'white' : props.theme.colors.primary};
      padding: 2px 8px;
      border-radius: 10px;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 10px;
    }
  }
`;

const ChatInput = styled.div`
  padding: 20px 24px;
  border-top: 1px solid ${props => props.theme.colors.borderLight};
  background: ${props => props.theme.colors.surface};
  box-shadow: ${props => props.theme.shadows.lg};
`;

const InputContainer = styled.div`
  display: flex;
  gap: 12px;
  align-items: center;
`;

// Wrapper to host the textarea and the + button inside it
const TextInputWrapper = styled.div`
  position: relative;
  flex: 1;
`;

// Adjust textarea to leave space for the + button on the left
const TextInput = styled.textarea`
  width: 100%;
  padding: 14px 20px 14px 56px; /* extra left padding for + button */
  border: 2px solid ${props => props.theme.colors.border};
  border-radius: 24px;
  background: ${props => props.theme.colors.surface};
  color: ${props => props.theme.colors.text};
  font-size: 15px;
  font-family: inherit;
  line-height: 1.5;
  resize: none;
  max-height: 120px;
  min-height: 48px;
  transition: all 0.3s ease;

  &:hover {
    border-color: ${props => props.theme.colors.primary};
    background: ${props => props.theme.colors.backgroundAlt};
  }

  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.primary};
    box-shadow: 0 0 0 4px ${props => props.theme.colors.primary}15;
    background: ${props => props.theme.colors.surface};
  }

  &::placeholder {
    color: ${props => props.theme.colors.textMuted};
    font-weight: 400;
  }

  &:disabled {
    background: ${props => props.theme.colors.backgroundAlt};
    cursor: not-allowed;
    opacity: 0.7;
  }
`;

// "+" button placed inside the textarea (left like ChatGPT)
const PlusInsideButton = styled(motion.button)`
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  border-radius: ${props => props.theme.borderRadius.full};
  border: 1px solid ${props => props.theme.colors.border};
  background: ${props => props.theme.colors.surface};
  color: ${props => props.theme.colors.textSecondary};
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: ${props => props.theme.colors.backgroundAlt};
    border-color: ${props => props.theme.colors.primary};
    color: ${props => props.theme.colors.primary};
  }

  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

// Stop button to cancel in-flight request
const StopButton = styled(motion.button)`
  width: 48px;
  height: 48px;
  border: none;
  border-radius: ${props => props.theme.borderRadius.full};
  background: linear-gradient(135deg, ${props => props.theme.colors.error} 0%, ${props => props.theme.colors.warning} 100%);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(220, 38, 38, 0.3);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background: linear-gradient(135deg, ${props => props.theme.colors.error} 0%, ${props => props.theme.colors.error} 100%);
    opacity: 0; transition: opacity 0.3s ease;
  }
  & > * { position: relative; z-index: 1; }
  &:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(220,38,38,0.4); &::before{opacity:1;} }
  &:active { transform: translateY(0); }
`;

const ChatLoadingIndicator = styled(motion.div)`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  background: white;
  border-radius: 18px 18px 18px 4px;
  color: ${props => props.theme.colors.textSecondary};
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid ${props => props.theme.colors.borderLight};
  max-width: fit-content;

  .dots {
    display: flex;
    gap: 3px;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${props => props.theme.colors.primary};
    animation: pulse 1.4s ease-in-out infinite both;
  }

  .dot:nth-child(1) { animation-delay: -0.32s; }
  .dot:nth-child(2) { animation-delay: -0.16s; }
  .dot:nth-child(3) { animation-delay: 0s; }

  @keyframes pulse {
    0%, 80%, 100% {
      transform: scale(0.6);
      opacity: 0.5;
    }
    40 {
      transform: scale(1);
      opacity: 1;
    }
  }
`;

const MicButton = styled(motion.button)`
  width: 48px;
  height: 48px;
  border: 2px solid ${props => props.active ? props.theme.colors.error : props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.full};
  background: ${props => props.active ? props.theme.colors.error : props.theme.colors.surface};
  color: ${props => props.active ? 'white' : props.theme.colors.textSecondary};
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: ${props => props.active ? '0 4px 20px rgba(220, 38, 38, 0.3)' : '0 2px 8px rgba(0, 0, 0, 0.1)'};

  &:hover {
    background: ${props => props.active ? props.theme.colors.error : props.theme.colors.backgroundAlt};
  }

  &:active { transform: translateY(0); }
`;

const SendButton = styled(motion.button)`
  width: 48px;
  height: 48px;
  border: none;
  border-radius: ${props => props.theme.borderRadius.full};
  background: linear-gradient(135deg, ${props => props.theme.colors.primary} 0%, ${props => props.theme.colors.primaryDark} 100%);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.3);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, ${props => props.theme.colors.primaryDark} 0%, ${props => props.theme.colors.professional} 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  & > * { position: relative; z-index: 1; }
  &:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4); &::before { opacity: 1; } }
  &:active { transform: translateY(0); }
  &:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: 0 2px 8px rgba(0,0,0,0.1); background: ${props => props.theme.colors.textMuted}; }
`;

function App() {
  // Core state
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  
  // Agent and chat mode state
  const [selectedAgents, setSelectedAgents] = useState([]);
  const [availableAgents, setAvailableAgents] = useState([]);
  const [maxTurns, setMaxTurns] = useState(2);
  const [responseFormat, setResponseFormat] = useState('user_friendly'); // 'user_friendly' or 'detailed'
  const [agentLoadError, setAgentLoadError] = useState(null);
  
  // Tools state
  const [selectedTools, setSelectedTools] = useState([]);
  
  // Memory toggle state
  const [enableMemory, setEnableMemory] = useState(false);
  
  // Streaming toggle state
  const [enableStreaming, setEnableStreaming] = useState(true); // Default to streaming enabled
  
  // Voice state
  const [isVoiceInputEnabled, setIsVoiceInputEnabled] = useState(false);
  const [isVoiceOutputEnabled, setIsVoiceOutputEnabled] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  
  // UI state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  
  // Services
  const [chatService] = useState(() => new ChatService());
  const [voiceService] = useState(() => new VoiceService());
  
  // Refs
  const messagesEndRef = useRef(null);
  const textInputRef = useRef(null);
  const fileInputRef = useRef(null);
  
  // Image attachment state
  const [attachedImage, setAttachedImage] = useState(null);

  // Local select styles (avoid linter false-positive)
  const customSelectStyles = {
    control: (provided, state) => ({
      ...provided,
      border: `1px solid ${state.isFocused ? theme.colors.primary : theme.colors.border}`,
      borderRadius: theme.borderRadius.md,
      boxShadow: state.isFocused ? `0 0 0 3px ${theme.colors.primary}20` : 'none',
      '&:hover': { borderColor: theme.colors.primary },
    }),
    multiValue: (provided) => ({
      ...provided,
      backgroundColor: theme.colors.primary,
      borderRadius: theme.borderRadius.sm,
    }),
    multiValueLabel: (provided) => ({
      ...provided,
      color: 'white',
      fontSize: '12px',
    }),
    multiValueRemove: (provided) => ({
      ...provided,
      color: 'white',
      '&:hover': { backgroundColor: theme.colors.primaryDark, color: 'white' },
    }),
  };

  // Inline preview chip to satisfy linter scope
  const PreviewChipLocal = styled.div`
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border: 1px solid ${props => props.theme.colors.border};
    border-radius: 9999px;
    background: ${props => props.theme.colors.backgroundAlt};
    color: ${props => props.theme.colors.textSecondary};
    font-size: 12px;
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  `;
  
  // Initialize
  useEffect(() => {
    loadAvailableAgents();
    initializeVoiceService();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadAvailableAgents = async () => {
    try {
      setAgentLoadError(null);
      const agents = await chatService.getAvailableAgents();
      setAvailableAgents(agents);
      // Don't auto-select any agent - let user choose
      // This prevents the duplicate selection issue
    } catch (error) {
      console.error('Failed to load agents:', error);
      const errorMsg = 'Failed to connect to server. Please check that your web server is running and listening on port 8000.';
      setAgentLoadError(errorMsg);
      setAvailableAgents([]);
    }
  };

  const initializeVoiceService = () => {
    // Set up voice input callbacks
    voiceService.onListeningStart = () => setIsListening(true);
    voiceService.onListeningEnd = () => setIsListening(false);
    voiceService.onTranscript = (transcript) => {
      if (transcript.isFinal) {
        setInputMessage(prev => prev + transcript.final + ' ');
      }
    };

    // Set up voice output callbacks
    voiceService.onSpeechStart = () => {
      setIsPlaying(true);
      setIsPaused(false);
    };
    voiceService.onSpeechEnd = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };
    voiceService.onSpeechPause = () => {
      setIsPaused(true);
    };
    voiceService.onSpeechResume = () => {
      setIsPaused(false);
    };

    // Error handling
    voiceService.onError = (error) => {
      console.error('Voice service error:', error);
      setIsListening(false);
      setIsPlaying(false);
      setIsPaused(false);
    };
  };

  const handleSendMessage = async () => {
    if ((!inputMessage.trim() && !attachedImage) || isLoading) return;

    const userMessage = {
      id: Date.now(),
      content: inputMessage || (attachedImage ? '[Sent an image]' : ''),
      isUser: true,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const agentIds = selectedAgents.map(agent => agent.id || agent.name);

      let response;
      if (attachedImage) {
        response = await chatService.sendMessageWithImage({
          message: userMessage.content || 'Image attached',
          imageFile: attachedImage,
          sessionId,
          agents: agentIds.length > 0 ? agentIds : null,
          maxTurns: selectedAgents.length > 1 ? maxTurns : null,
          format: selectedAgents.length > 1 ? responseFormat : null,
          enableMemory: enableMemory
        });
        // Clear image after sending
        setAttachedImage(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      } else {
        response = await chatService.sendMessage(
          userMessage.content,
          sessionId,
          agentIds.length > 0 ? agentIds : null,
          selectedAgents.length > 1 ? maxTurns : null,
          selectedAgents.length > 1 ? responseFormat : null,
          enableMemory,
          enableStreaming,  // Pass streaming flag
          selectedTools.length > 0 ? selectedTools : null  // Pass selected tools
        );
      }

      // Handle different response formats
      if (responseFormat === 'detailed' && response.responses) {
        // Detailed format - show all agent responses
        const detailedMessages = response.responses.map((resp, idx) => ({
          id: Date.now() + idx + 1,
          content: resp.content,
          isUser: false,
          timestamp: resp.metadata?.timestamp || response.timestamp,
          agent: resp.agent,
          metadata: resp.metadata || {},
          turn: resp.metadata?.turn
        }));
        setMessages(prev => [...prev, ...detailedMessages]);
      } else {
        // User-friendly format - single synthesized response
        const assistantMessage = {
          id: Date.now() + 1,
          content: response.content,
          isUser: false,
          timestamp: response.timestamp,
          agent: response.agent || response.speaker,
          metadata: response.metadata || {},
          format: response.format
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
      
      setSessionId(response.sessionId);

      // Play voice response if enabled
      if (isVoiceOutputEnabled && response.content) {
        voiceService.speak(response.content);
      }

    } catch (error) {
      if (error.message === 'Request canceled') {
        setMessages(prev => [...prev, { id: Date.now() + 1, content: 'Request canceled.', isUser: false, timestamp: new Date().toISOString(), isError: true }]);
      } else {
        setMessages(prev => [...prev, { id: Date.now() + 1, content: `Error: ${error.message}`, isUser: false, timestamp: new Date().toISOString(), isError: true }]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = () => {
    chatService.cancelCurrentRequest();
    setIsLoading(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const toggleVoiceInput = () => {
    if (isListening) {
      voiceService.stopListening();
    } else {
      voiceService.startListening();
    }
  };

  const toggleVoicePlayback = () => {
    if (isPlaying && !isPaused) {
      // Currently playing, so pause it
      voiceService.pauseSpeech();
    } else if (isPaused) {
      // Currently paused, so resume it
      voiceService.resumeSpeech();
    } else {
      // Not playing, replay last message if available
      replayLastMessage();
    }
  };

  const stopVoicePlayback = () => {
    voiceService.stopSpeaking();
  };

  const replayLastMessage = () => {
    const lastAssistantMessage = messages
      .filter(msg => !msg.isUser)
      .pop();
    
    if (lastAssistantMessage && isVoiceOutputEnabled) {
      voiceService.speak(lastAssistantMessage.content);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSessionId(null);
    voiceService.stopSpeaking();
  };

  const formatAgentOptions = (agents) => {
    return agents.map(agent => ({
      value: agent.name, // Use name as the identifier
      label: agent.name,
      description: agent.description,
      ...agent,
      id: agent.name // Add id field for backward compatibility
    }));
  };

  const onSelectFile = (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setAttachedImage(file);
  };

  return (
    <ThemeProvider theme={theme}>
      <GlobalStyle />
      <AppContainer>
        <Sidebar
          collapsed={isSidebarCollapsed}
          initial={{ x: -320 }}
          animate={{ x: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
          <SidebarToggle
            collapsed={isSidebarCollapsed}
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title={isSidebarCollapsed ? "Show sidebar" : "Hide sidebar"}
          >
            {isSidebarCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
          </SidebarToggle>
          
          <SidebarContent collapsed={isSidebarCollapsed}>
            <SidebarHeader>
              <h1>Agent Chat Pro</h1>
              <p>Enterprise Multi-Agent Platform</p>
            </SidebarHeader>

          <AgentSection>
            <h3>
              <Bot size={16} />
              {selectedAgents.length > 1 ? 'Group Chat' : 'Select Agents'}
            </h3>
            {agentLoadError ? (
              <ErrorMessage>
                <AlertCircle size={18} />
                <div className="error-content">
                  <div className="error-title">Connection Error</div>
                  <div className="error-details">{agentLoadError}</div>
                </div>
              </ErrorMessage>
            ) : (
              <>
                <Select
                  isMulti
                  value={selectedAgents.map(agent => ({
                    value: agent.id,
                    label: agent.name,
                    ...agent
                  }))}
                  onChange={(selected) => setSelectedAgents(selected || [])}
                  options={formatAgentOptions(availableAgents)}
                  styles={customSelectStyles}
                  placeholder="Choose agents..."
                  isSearchable
                  closeMenuOnSelect={false}
                  isDisabled={availableAgents.length === 0}
                />
                
                {/* Memory Toggle */}
                <VoiceToggle style={{ marginTop: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '20px' }}>{enableMemory ? '🧠' : '💭'}</span>
                    <span>Agent Memory</span>
                  </div>
                  <ToggleSwitch
                    active={enableMemory}
                    onClick={() => setEnableMemory(!enableMemory)}
                    whileTap={{ scale: 0.95 }}
                  />
                </VoiceToggle>
                {enableMemory && (
                  <div style={{ 
                    fontSize: '12px', 
                    color: theme.colors.textSecondary, 
                    marginTop: '8px',
                    padding: '8px 12px',
                    background: theme.colors.backgroundAlt,
                    borderRadius: theme.borderRadius.sm,
                    borderLeft: `3px solid ${theme.colors.primary}`
                  }}>
                    💡 Agent will remember your name and preferences across messages
                  </div>
                )}
                
                {/* Streaming Toggle */}
                <VoiceToggle style={{ marginTop: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '20px' }}>{enableStreaming ? '⚡' : '📦'}</span>
                    <span>Streaming Mode</span>
                  </div>
                  <ToggleSwitch
                    active={enableStreaming}
                    onClick={() => setEnableStreaming(!enableStreaming)}
                    whileTap={{ scale: 0.95 }}
                  />
                </VoiceToggle>
                {enableStreaming && (
                  <div style={{ 
                    fontSize: '12px', 
                    color: theme.colors.textSecondary, 
                    marginTop: '8px',
                    padding: '8px 12px',
                    background: theme.colors.backgroundAlt,
                    borderRadius: theme.borderRadius.sm,
                    borderLeft: `3px solid ${theme.colors.secondary}`
                  }}>
                    ⚡ Receive responses in real-time as they're generated
                  </div>
                )}
                
                {selectedAgents.length > 1 && (
                  <>
                    <p style={{ fontSize: '12px', color: theme.colors.textSecondary, marginTop: '8px' }}>
                      Multiple agents selected - they will collaborate on responses
                    </p>
                    <MaxTurnsControl>
                      <label>
                        <span>Max Turns</span>
                        <span style={{ fontSize: '12px', fontWeight: 'normal', color: theme.colors.textMuted }}>
                          {maxTurns} turn{maxTurns !== 1 ? 's' : ''}
                        </span>
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={maxTurns}
                        onChange={(e) => setMaxTurns(Math.max(1, Math.min(10, parseInt(e.target.value) || 1)))}
                      />
                      <div className="help-text">
                        Controls how many conversation turns agents can take. Higher values allow more collaboration but may increase response time.
                      </div>
                    </MaxTurnsControl>

                    <FormatSelector>
                      <label>Response Format</label>
                      <div className="format-options">
                        <div 
                          className={`format-option ${responseFormat === 'user_friendly' ? 'active' : ''}`}
                          onClick={() => setResponseFormat('user_friendly')}
                        >
                          <div className="format-title">User Friendly</div>
                          <div className="format-description">Synthesized, clean response</div>
                        </div>
                        <div 
                          className={`format-option ${responseFormat === 'detailed' ? 'active' : ''}`}
                          onClick={() => setResponseFormat('detailed')}
                        >
                          <div className="format-title">Detailed</div>
                          <div className="format-description">Full conversation history</div>
                        </div>
                      </div>
                      <div className="help-text">
                        {responseFormat === 'user_friendly' 
                          ? '✨ Shows a synthesized response from all agents (recommended)'
                          : '🔍 Shows all individual agent responses and conversation turns'}
                      </div>
                    </FormatSelector>
                  </>
                )}
              </>
            )}
          </AgentSection>

          {/* Tools Selector - Local and MCP Tools */}
          <ToolsSelector
            chatService={chatService}
            selectedTools={selectedTools}
            onToolsChange={setSelectedTools}
            disabled={isLoading}
          />

          <VoiceSection>
            <h3>
              <Volume2 size={16} />
              Voice Controls
            </h3>
            <VoiceControls>
              <VoiceToggle>
                <span>Voice Input</span>
                <ToggleSwitch
                  active={isVoiceInputEnabled}
                  onClick={() => setIsVoiceInputEnabled(!isVoiceInputEnabled)}
                  whileTap={{ scale: 0.95 }}
                />
              </VoiceToggle>
              
              <VoiceToggle>
                <span>Voice Output</span>
                <ToggleSwitch
                  active={isVoiceOutputEnabled}
                  onClick={() => {
                    const newState = !isVoiceOutputEnabled;
                    setIsVoiceOutputEnabled(newState);
                    // Stop any current speech when disabling voice output
                    if (!newState) {
                      voiceService.stopSpeaking();
                    }
                  }}
                  whileTap={{ scale: 0.95 }}
                />
              </VoiceToggle>

              {isVoiceOutputEnabled && (
                <div style={{ marginTop: '12px' }}>
                  <p style={{ fontSize: '12px', color: theme.colors.textSecondary, marginBottom: '8px', fontWeight: '500' }}>
                    Playback Controls
                  </p>
                  <VoicePlaybackControls enabled={isVoiceOutputEnabled}>
                    <VoiceButton
                      active={isPlaying && !isPaused}
                      onClick={toggleVoicePlayback}
                      disabled={!isVoiceOutputEnabled}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      title={isPlaying && !isPaused ? "Pause" : "Play"}
                    >
                      {isPlaying && !isPaused ? <Pause size={18} /> : <Play size={18} />}
                    </VoiceButton>
                    
                    <VoiceButton
                      onClick={stopVoicePlayback}
                      disabled={!isVoiceOutputEnabled || (!isPlaying && !isPaused)}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      title="Stop"
                    >
                      <Square size={18} />
                    </VoiceButton>
                    
                    <VoiceButton
                      onClick={replayLastMessage}
                      disabled={!isVoiceOutputEnabled || messages.filter(m => !m.isUser).length === 0}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      title="Replay last message"
                    >
                      <RotateCcw size={18} />
                    </VoiceButton>
                  </VoicePlaybackControls>
                </div>
              )}
            </VoiceControls>
          </VoiceSection>

          {/* Use the SafetyTester component with tabbed interface */}
          <SafetyTester chatService={chatService} />
          </SidebarContent>
        </Sidebar>

        <MainContent>
          <ChatHeader>
            <h2>
              {isSidebarCollapsed && (
                <MenuButton
                  onClick={() => setIsSidebarCollapsed(false)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Menu size={20} />
                </MenuButton>
              )}
              {selectedAgents.length > 1 ? <Users size={20} /> : <Bot size={20} />}
              {selectedAgents.length > 1 
                ? `Group Chat with ${selectedAgents.map(a => a.name).join(', ')}`
                : `Chat with ${selectedAgents.length > 0 ? selectedAgents[0].name : 'AI Agent'}`
              }
            </h2>
            <ChatActions>
              <ActionButton
                onClick={clearChat}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Trash2 size={16} />
                Clear
              </ActionButton>
            </ChatActions>
          </ChatHeader>

          <ChatMessages>
            <AnimatePresence>
              {messages.map((message) => (
                <Message
                  key={message.id}
                  isUser={message.isUser}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <MessageAvatar isUser={message.isUser}>
                    {message.isUser ? 'U' : (message.agent ? message.agent.charAt(0).toUpperCase() : 'A')}
                  </MessageAvatar>
                  <MessageContent isUser={message.isUser}>
                    {message.format === 'markdown' ? (
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    ) : (
                      message.content
                    )}
                    <div className="message-meta">
                      {message.turn !== undefined && <span className="turn-badge">Turn {message.turn}</span>}
                      {message.agent && <span>Agent: {message.agent}</span>}
                      <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </MessageContent>
                </Message>
              ))}
            </AnimatePresence>
            {isLoading && (
              <ChatLoadingIndicator
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <Bot size={16} />
                Agent is thinking
                <div className="dots">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </ChatLoadingIndicator>
            )}
            <div ref={messagesEndRef} />
          </ChatMessages>

          <ChatInput>
            <InputContainer>
              <TextInputWrapper>
                <TextInput
                  ref={textInputRef}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={isListening ? 'Listening...' : 'Type your message...'}
                  disabled={isLoading || isListening}
                />
                
                {attachedImage && (
                  <PreviewChipLocal>
                    <ImageIcon size={14} />
                    {attachedImage.name} ({Math.round(attachedImage.size / 1024)} KB)
                  </PreviewChipLocal>
                )}

                <PlusInsideButton
                  onClick={() => fileInputRef.current && fileInputRef.current.click()}
                  title="Attach an image"
                  disabled={isLoading}
                >
                  <Plus size={18} />
                </PlusInsideButton>
                <input
                  id="file-input"
                  type="file"
                  accept="image/*"
                  ref={fileInputRef}
                  onChange={onSelectFile}
                  style={{ display: 'none' }}
                  disabled={isLoading}
                />
              </TextInputWrapper>

              {isVoiceInputEnabled && (
                <MicButton
                  active={isListening}
                  onClick={toggleVoiceInput}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  disabled={isLoading}
                >
                  {isListening ? <MicOff size={20} /> : <Mic size={20} />}
                </MicButton>
              )}

              {isLoading ? (
                <StopButton
                  onClick={handleStop}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  title="Stop request"
                >
                  <X size={20} />
                </StopButton>
              ) : (
                <SendButton
                  onClick={handleSendMessage}
                  disabled={(!inputMessage.trim() && !attachedImage) || isLoading}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  title="Send"
                >
                  <Send size={20} />
                </SendButton>
              )}
            </InputContainer>
          </ChatInput>
        </MainContent>
      </AppContainer>
    </ThemeProvider>
  );
}

export default App;