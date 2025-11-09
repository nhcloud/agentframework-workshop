import React, { useState, useRef } from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { Shield, Upload, FileText, AlertCircle, ImageIcon } from 'lucide-react';

const SafetySection = styled.div`
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

const SafetyTestControls = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const SafetyButton = styled(motion.button)`
  padding: 10px 16px;
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.md};
  background: ${props => props.theme.colors.surface};
  color: ${props => props.theme.colors.text};
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;

  &:hover {
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
  min-height: 80px;
  padding: 10px 12px;
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.md};
  font-size: 13px;
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

const SafetyResultBox = styled.div`
  padding: 12px;
  background: ${props => props.isSafe ? props.theme.colors.success + '15' : props.theme.colors.error + '15'};
  border: 1px solid ${props => props.isSafe ? props.theme.colors.success : props.theme.colors.error};
  border-radius: ${props => props.theme.borderRadius.md};
  color: ${props => props.theme.colors.text};
  font-size: 12px;
  line-height: 1.5;

  .result-header {
    font-weight: 600;
    color: ${props => props.isSafe ? props.theme.colors.success : props.theme.colors.error};
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .result-details {
    font-size: 11px;
    opacity: 0.9;
  }

  .severity-item {
    display: flex;
    justify-content: space-between;
    margin: 4px 0;
    padding: 2px 4px;
    background: rgba(0,0,0,0.05);
    border-radius: 4px;
  }

  .flagged-categories {
    margin-top: 8px;
    font-weight: 600;
    color: ${props => props.theme.colors.error};
  }
`;

const FileUploadButton = styled.label`
  padding: 10px 16px;
  border: 2px dashed ${props => props.theme.colors.border};
  border-radius: ${props => props.theme.borderRadius.md};
  background: ${props => props.theme.colors.backgroundAlt};
  color: ${props => props.theme.colors.text};
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
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

function SafetyTester({ chatService }) {
  const [safetyTestText, setSafetyTestText] = useState('');
  const [safetyImageFile, setSafetyImageFile] = useState(null);
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
    }
  };

  return (
    <SafetySection>
      <h3>
        <Shield size={16} />
        Content Safety Testing
      </h3>
      <SafetyTestControls>
        <div>
          <SafetyTextArea
            placeholder="Enter text to scan for safety..."
            value={safetyTestText}
            onChange={(e) => setSafetyTestText(e.target.value)}
          />
          <SafetyButton
            onClick={testSafetyText}
            disabled={!safetyTestText.trim() || isSafetyTesting}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            style={{ marginTop: '8px', width: '100%' }}
          >
            <FileText size={16} />
            {isSafetyTesting ? 'Scanning...' : 'Scan Text'}
          </SafetyButton>
        </div>

        {safetyTextResult && (
          <SafetyResultBox isSafe={safetyTextResult.isSafe && !safetyTextResult.error}>
            {safetyTextResult.error ? (
              <>
                <div className="result-header">
                  <AlertCircle size={16} />
                  Error
                </div>
                <div className="result-details">{safetyTextResult.error}</div>
              </>
            ) : (
              <>
                <div className="result-header">
                  <Shield size={16} />
                  {safetyTextResult.isSafe ? 'Safe Content' : 'Unsafe Content Detected'}
                </div>
                <div className="result-details">
                  <div><strong>Highest Severity:</strong> {safetyTextResult.highestSeverity}</div>
                  <div><strong>Highest Category:</strong> {safetyTextResult.highestCategory || 'None'}</div>
                  {safetyTextResult.categorySeverities && Object.keys(safetyTextResult.categorySeverities).length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <strong>Category Severities:</strong>
                      {Object.entries(safetyTextResult.categorySeverities).map(([category, severity]) => (
                        <div key={category} className="severity-item">
                          <span>{category}</span>
                          <span>{severity}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {safetyTextResult.flaggedCategories && safetyTextResult.flaggedCategories.length > 0 && (
                    <div className="flagged-categories">
                      Flagged: {safetyTextResult.flaggedCategories.join(', ')}
                    </div>
                  )}
                  {safetyTextResult.blocklistMatches && safetyTextResult.blocklistMatches.length > 0 && (
                    <div className="flagged-categories">
                      Blocklist Matches: {safetyTextResult.blocklistMatches.length}
                    </div>
                  )}
                </div>
              </>
            )}
          </SafetyResultBox>
        )}

        <div style={{ marginTop: '12px' }}>
          <FileUploadButton>
            <Upload size={16} />
            {safetyImageFile ? `Selected: ${safetyImageFile.name}` : 'Select Image to Scan'}
            <input
              type="file"
              accept="image/*"
              ref={safetyImageInputRef}
              onChange={handleSafetyImageSelect}
            />
          </FileUploadButton>
          {safetyImageFile && (
            <SafetyButton
              onClick={testSafetyImage}
              disabled={isSafetyTesting}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              style={{ marginTop: '8px', width: '100%' }}
            >
              <ImageIcon size={16} />
              {isSafetyTesting ? 'Scanning...' : 'Scan Image'}
            </SafetyButton>
          )}
        </div>

        {safetyImageResult && (
          <SafetyResultBox isSafe={safetyImageResult.isSafe && !safetyImageResult.error}>
            {safetyImageResult.error ? (
              <>
                <div className="result-header">
                  <AlertCircle size={16} />
                  Error
                </div>
                <div className="result-details">{safetyImageResult.error}</div>
              </>
            ) : (
              <>
                <div className="result-header">
                  <Shield size={16} />
                  {safetyImageResult.isSafe ? 'Safe Image' : 'Unsafe Image Detected'}
                </div>
                <div className="result-details">
                  <div><strong>Highest Severity:</strong> {safetyImageResult.highestSeverity}</div>
                  <div><strong>Highest Category:</strong> {safetyImageResult.highestCategory || 'None'}</div>
                  {safetyImageResult.categorySeverities && Object.keys(safetyImageResult.categorySeverities).length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <strong>Category Severities:</strong>
                      {Object.entries(safetyImageResult.categorySeverities).map(([category, severity]) => (
                        <div key={category} className="severity-item">
                          <span>{category}</span>
                          <span>{severity}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {safetyImageResult.flaggedCategories && safetyImageResult.flaggedCategories.length > 0 && (
                    <div className="flagged-categories">
                      Flagged: {safetyImageResult.flaggedCategories.join(', ')}
                    </div>
                  )}
                </div>
              </>
            )}
          </SafetyResultBox>
        )}
      </SafetyTestControls>
    </SafetySection>
  );
}

export default SafetyTester;
