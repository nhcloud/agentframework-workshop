import React, { useState, useRef } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Upload, FileText, AlertCircle, Image as ImageIcon, X } from 'lucide-react';

const SafetySection = styled.div`
  padding: 20px;
  border-bottom: 1px solid ${props => props.theme.colors.borderLight};
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 400px);
  overflow: hidden;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: ${props => props.theme.colors.text};
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
`;

const TabContainer = styled.div`
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  border-bottom: 2px solid ${props => props.theme.colors.borderLight};
  flex-shrink: 0;
`;

const Tab = styled(motion.button)`
  padding: 10px 16px;
  border: none;
  background: transparent;
  color: ${props => props.active ? props.theme.colors.primary : props.theme.colors.textSecondary};
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
  transition: all 0.2s ease;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;

  &:hover {
    color: ${props => props.theme.colors.primary};
  }

  ${props => props.active && `
    color: ${props.theme.colors.primary};
    border-bottom-color: ${props.theme.colors.primary};
  `}
`;

const TabContent = styled(motion.div)`
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
  padding-right: 4px;

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

const CompactInputGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const SafetyButton = styled(motion.button)`
  padding: 8px 14px;
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.md};
  background: ${props => props.theme.colors.surface};
  color: ${props => props.theme.colors.text};
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s ease;
  width: 100%;

  &:hover:not(:disabled) {
    background: ${props => props.theme.colors.primary};
    color: white;
    border-color: ${props => props.theme.colors.primary};
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const SafetyTextArea = styled.textarea`
  width: 100%;
  min-height: 70px;
  max-height: 120px;
  padding: 10px 12px;
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.md};
  font-size: 12px;
  color: ${props => props.theme.colors.text};
  background: ${props => props.theme.colors.surface};
  font-family: inherit;
  resize: vertical;
  transition: all 0.2s ease;

  &:focus {
    outline: none;
    border-color: ${props => props.theme.colors.primary};
    box-shadow: 0 0 0 3px ${props => props.theme.colors.primary}20;
  }

  &::placeholder {
    color: ${props => props.theme.colors.textMuted};
  }
`;

const CompactResultBox = styled(motion.div)`
  padding: 10px;
  background: ${props => props.isSafe ? props.theme.colors.success + '15' : props.theme.colors.error + '15'};
  border: 1px solid ${props => props.isSafe ? props.theme.colors.success : props.theme.colors.error};
  border-radius: ${props => props.theme.borderRadius.md};
  color: ${props => props.theme.colors.text};
  font-size: 11px;
  line-height: 1.4;
  position: relative;
  max-height: 250px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: ${props => props.theme.colors.border};
    border-radius: 2px;
  }

  .result-header {
    font-weight: 600;
    color: ${props => props.isSafe ? props.theme.colors.success : props.theme.colors.error};
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    position: sticky;
    top: 0;
    background: inherit;
    padding-bottom: 4px;
  }

  .result-details {
    font-size: 10px;
    opacity: 0.9;
  }

  .severity-item {
    display: flex;
    justify-content: space-between;
    margin: 3px 0;
    padding: 2px 4px;
    background: rgba(0,0,0,0.05);
    border-radius: 3px;
    font-size: 10px;
  }

  .flagged-categories {
    margin-top: 6px;
    font-weight: 600;
    font-size: 10px;
    color: ${props => props.theme.colors.error};
  }
`;

const CloseButton = styled.button`
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  opacity: 0.6;

  &:hover {
    opacity: 1;
  }
`;

const FileUploadButton = styled.label`
  padding: 8px 14px;
  border: 2px dashed ${props => props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.md};
  background: ${props => props.theme.colors.backgroundAlt};
  color: ${props => props.theme.colors.text};
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  text-align: center;
  justify-content: center;

  &:hover {
    background: ${props => props.theme.colors.primary}10;
    border-color: ${props => props.theme.colors.primary};
    color: ${props => props.theme.colors.primary};
  }

  input[type="file"] {
    display: none;
  }
`;

const ImagePreview = styled.div`
  width: 100%;
  max-height: 150px;
  border-radius: ${props => props.theme.borderRadius.md};
  overflow: hidden;
  border: 1px solid ${props => props.theme.colors.border};
  background: ${props => props.theme.colors.backgroundAlt};
  display: flex;
  align-items: center;
  justify-content: center;

  img {
    max-width: 100%;
    max-height: 150px;
    object-fit: contain;
  }
`;

function SafetyTester({ chatService }) {
  const [activeTab, setActiveTab] = useState('text');
  const [safetyTestText, setSafetyTestText] = useState('');
  const [safetyImageFile, setSafetyImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [safetyTextResult, setSafetyTextResult] = useState(null);
  const [safetyImageResult, setSafetyImageResult] = useState(null);
  const [isSafetyTesting, setIsSafetyTesting] = useState(false);
  const safetyImageInputRef = useRef(null);

  const testSafetyText = async () => {
    if (!safetyTestText.trim()) return;
    
    setIsSafetyTesting(true);
    setSafetyTextResult(null);
    
    try {
      const response = await chatService.api.post('/safety/scan-text', {
        text: safetyTestText
      });
      
      setSafetyTextResult(response.data);
    } catch (error) {
      setSafetyTextResult({
        error: error.response?.data?.detail || error.message || 'Failed to scan text'
      });
    } finally {
      setIsSafetyTesting(false);
    }
  };

  const testSafetyImage = async () => {
    if (!safetyImageFile) return;
    
    setIsSafetyTesting(true);
    setSafetyImageResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', safetyImageFile);
      
      const response = await chatService.uploadApi.post('/safety/scan-image', formData);
      
      setSafetyImageResult(response.data);
    } catch (error) {
      setSafetyImageResult({
        error: error.response?.data?.detail || error.message || 'Failed to scan image'
      });
    } finally {
      setIsSafetyTesting(false);
    }
  };

  const handleSafetyImageSelect = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      setSafetyImageFile(file);
      setSafetyImageResult(null);
      
      // Create image preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const clearImageSelection = () => {
    setSafetyImageFile(null);
    setImagePreview(null);
    setSafetyImageResult(null);
    if (safetyImageInputRef.current) {
      safetyImageInputRef.current.value = '';
    }
  };

  const ResultDisplay = ({ result, onClose }) => {
    if (!result) return null;

    return (
      <CompactResultBox 
        isSafe={result.isSafe && !result.error}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {result.error ? (
          <>
            <div className="result-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertCircle size={14} />
                <span>Error</span>
              </div>
              <CloseButton onClick={onClose} title="Clear result">
                <X size={14} />
              </CloseButton>
            </div>
            <div className="result-details">{result.error}</div>
          </>
        ) : (
          <>
            <div className="result-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Shield size={14} />
                <span>{result.isSafe ? 'Safe Content' : 'Unsafe Content Detected'}</span>
              </div>
              <CloseButton onClick={onClose} title="Clear result">
                <X size={14} />
              </CloseButton>
            </div>
            <div className="result-details">
              <div><strong>Severity:</strong> {result.highestSeverity}/7</div>
              <div><strong>Category:</strong> {result.highestCategory || 'None'}</div>
              {result.categorySeverities && Object.keys(result.categorySeverities).length > 0 && (
                <div style={{ marginTop: '6px' }}>
                  <strong>Categories:</strong>
                  {Object.entries(result.categorySeverities).map(([category, severity]) => (
                    <div key={category} className="severity-item">
                      <span>{category}</span>
                      <span>{severity}</span>
                    </div>
                  ))}
                </div>
              )}
              {result.flaggedCategories && result.flaggedCategories.length > 0 && (
                <div className="flagged-categories">
                  Flagged: {result.flaggedCategories.join(', ')}
                </div>
              )}
              {result.blocklistMatches && result.blocklistMatches.length > 0 && (
                <div className="flagged-categories">
                  Blocklist: {result.blocklistMatches.length} match(es)
                </div>
              )}
            </div>
          </>
        )}
      </CompactResultBox>
    );
  };

  return (
    <SafetySection>
      <h3>
        <Shield size={16} />
        Content Safety
      </h3>
      
      <TabContainer>
        <Tab
          active={activeTab === 'text'}
          onClick={() => setActiveTab('text')}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <FileText size={14} />
          Text
        </Tab>
        <Tab
          active={activeTab === 'image'}
          onClick={() => setActiveTab('image')}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <ImageIcon size={14} />
          Image
        </Tab>
      </TabContainer>

      <AnimatePresence mode="wait">
        {activeTab === 'text' && (
          <TabContent
            key="text-tab"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={{ duration: 0.2 }}
          >
            <CompactInputGroup>
              <SafetyTextArea
                placeholder="Enter text to scan..."
                value={safetyTestText}
                onChange={(e) => setSafetyTestText(e.target.value)}
              />
              <SafetyButton
                onClick={testSafetyText}
                disabled={!safetyTestText.trim() || isSafetyTesting}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
              >
                <FileText size={14} />
                {isSafetyTesting ? 'Scanning...' : 'Scan Text'}
              </SafetyButton>
            </CompactInputGroup>

            <ResultDisplay 
              result={safetyTextResult} 
              onClose={() => setSafetyTextResult(null)} 
            />
          </TabContent>
        )}

        {activeTab === 'image' && (
          <TabContent
            key="image-tab"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.2 }}
          >
            <CompactInputGroup>
              {imagePreview && (
                <ImagePreview>
                  <img src={imagePreview} alt="Preview" />
                </ImagePreview>
              )}
              
              <FileUploadButton>
                <Upload size={14} />
                {safetyImageFile ? `${safetyImageFile.name.substring(0, 20)}...` : 'Select Image'}
                <input
                  type="file"
                  accept="image/*"
                  ref={safetyImageInputRef}
                  onChange={handleSafetyImageSelect}
                />
              </FileUploadButton>

              {safetyImageFile && (
                <>
                  <SafetyButton
                    onClick={testSafetyImage}
                    disabled={isSafetyTesting}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <ImageIcon size={14} />
                    {isSafetyTesting ? 'Scanning...' : 'Scan Image'}
                  </SafetyButton>
                  
                  <SafetyButton
                    onClick={clearImageSelection}
                    disabled={isSafetyTesting}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    style={{ 
                      background: 'transparent',
                      color: '#dc2626',
                      borderColor: '#dc2626'
                    }}
                  >
                    <X size={14} />
                    Clear
                  </SafetyButton>
                </>
              )}
            </CompactInputGroup>

            <ResultDisplay 
              result={safetyImageResult} 
              onClose={() => {
                setSafetyImageResult(null);
                clearImageSelection();
              }} 
            />
          </TabContent>
        )}
      </AnimatePresence>
    </SafetySection>
  );
}

export default SafetyTester;
