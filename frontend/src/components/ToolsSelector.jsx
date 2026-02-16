import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { Wrench, Server, Code, Globe, ChevronDown, ChevronRight, Check, RefreshCw, Terminal, Wifi, Link2, Zap } from 'lucide-react';

const ToolsContainer = styled.div`
  padding: 16px;
  border-bottom: 1px solid ${props => props.theme.colors.borderLight};
  flex-shrink: 0;
`;

const ToolsHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  cursor: pointer;

  h3 {
    font-size: 14px;
    font-weight: 600;
    color: ${props => props.theme.colors.text};
    display: flex;
    align-items: center;
    gap: 8px;
  }
`;

const ToolsCount = styled.span`
  background: ${props => props.theme.colors.primary};
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
`;

const ToolsSummary = styled.div`
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
`;

const SummaryBadge = styled.span`
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  background: ${props => {
    switch(props.type) {
      case 'local': return props.theme.colors.success + '15';
      case 'stdio': return props.theme.colors.primary + '15';
      case 'sse': return props.theme.colors.warning + '15';
      default: return props.theme.colors.border;
    }
  }};
  color: ${props => {
    switch(props.type) {
      case 'local': return props.theme.colors.success;
      case 'stdio': return props.theme.colors.primary;
      case 'sse': return props.theme.colors.warning;
      default: return props.theme.colors.textSecondary;
    }
  }};
  border: 1px solid ${props => {
    switch(props.type) {
      case 'local': return props.theme.colors.success + '30';
      case 'stdio': return props.theme.colors.primary + '30';
      case 'sse': return props.theme.colors.warning + '30';
      default: return props.theme.colors.border;
    }
  }};
`;

const RefreshButton = styled.button`
  background: none;
  border: none;
  color: ${props => props.theme.colors.textSecondary};
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  
  &:hover {
    background: ${props => props.theme.colors.backgroundAlt};
    color: ${props => props.theme.colors.primary};
  }

  &.loading {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;

const CategoryContainer = styled.div`
  margin-bottom: 8px;
  border: 1px solid ${props => props.theme.colors.border};
  border-radius: 8px;
  overflow: hidden;
`;

const CategoryHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: ${props => props.theme.colors.backgroundAlt};
  cursor: pointer;
  user-select: none;

  &:hover {
    background: ${props => props.theme.colors.surfaceHover};
  }

  .category-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .category-name {
    font-size: 13px;
    font-weight: 500;
    color: ${props => props.theme.colors.text};
  }

  .category-count {
    font-size: 11px;
    color: ${props => props.theme.colors.textSecondary};
    background: ${props => props.theme.colors.border};
    padding: 2px 6px;
    border-radius: 8px;
  }
`;

const CategoryIcon = styled.span`
  display: flex;
  align-items: center;
  color: ${props => {
    switch(props.category) {
      case 'local': return props.theme.colors.success;
      case 'mcp-local': return props.theme.colors.primary;
      case 'mcp-stdio': return props.theme.colors.primary;
      case 'mcp-remote': return props.theme.colors.warning;
      case 'mcp-sse': return props.theme.colors.warning;
      case 'mcp-bridge': return props.theme.colors.info || '#17a2b8';
      default: return props.theme.colors.textSecondary;
    }
  }};
`;

const TransportBadge = styled.span`
  font-size: 9px;
  padding: 2px 5px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
  background: ${props => {
    switch(props.transport) {
      case 'stdio': return props.theme.colors.primary + '20';
      case 'sse': 
      case 'http': return props.theme.colors.warning + '20';
      case 'native': return props.theme.colors.success + '20';
      default: return props.theme.colors.border;
    }
  }};
  color: ${props => {
    switch(props.transport) {
      case 'stdio': return props.theme.colors.primary;
      case 'sse': 
      case 'http': return props.theme.colors.warning;
      case 'native': return props.theme.colors.success;
      default: return props.theme.colors.textSecondary;
    }
  }};
`;

const ToolsList = styled.div`
  max-height: ${props => props.expanded ? '500px' : '0'};
  overflow-y: auto;
  overflow-x: hidden;
  transition: max-height 0.3s ease;
  
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
`;

const ToolItem = styled.div`
  display: flex;
  align-items: flex-start;
  padding: 10px 12px;
  border-top: 1px solid ${props => props.theme.colors.borderLight};
  cursor: pointer;
  transition: background 0.2s ease;

  &:hover {
    background: ${props => props.theme.colors.surfaceHover};
  }

  &.selected {
    background: ${props => props.theme.colors.primary}10;
  }
`;

const ToolCheckbox = styled.div`
  width: 18px;
  height: 18px;
  border: 2px solid ${props => props.selected ? props.theme.colors.primary : props.theme.colors.border};
  border-radius: 4px;
  margin-right: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${props => props.selected ? props.theme.colors.primary : 'transparent'};
  transition: all 0.2s ease;
  flex-shrink: 0;

  svg {
    color: white;
  }
`;

const ToolInfo = styled.div`
  flex: 1;
  min-width: 0;

  .tool-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 2px;
  }

  .tool-name {
    font-size: 13px;
    font-weight: 500;
    color: ${props => props.theme.colors.text};
  }

  .tool-description {
    font-size: 11px;
    color: ${props => props.theme.colors.textSecondary};
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .tool-source {
    font-size: 10px;
    color: ${props => props.theme.colors.textMuted};
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
  }
`;

const SelectAllButton = styled.button`
  background: none;
  border: none;
  color: ${props => props.theme.colors.primary};
  font-size: 11px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;

  &:hover {
    background: ${props => props.theme.colors.primary}10;
  }
`;

const NoToolsMessage = styled.div`
  padding: 20px;
  text-align: center;
  color: ${props => props.theme.colors.textSecondary};
  font-size: 13px;
`;

const ErrorMessage = styled.div`
  padding: 12px;
  background: ${props => props.theme.colors.error}10;
  border: 1px solid ${props => props.theme.colors.error}30;
  border-radius: 6px;
  color: ${props => props.theme.colors.error};
  font-size: 12px;
  margin-top: 8px;
`;

const ServerStatusContainer = styled.div`
  margin-top: 12px;
  padding: 10px;
  background: ${props => props.theme.colors.backgroundAlt};
  border-radius: 6px;
  border: 1px solid ${props => props.theme.colors.border};
`;

const ServerStatusHeader = styled.div`
  font-size: 11px;
  font-weight: 600;
  color: ${props => props.theme.colors.textSecondary};
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const ServerStatusItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid ${props => props.theme.colors.borderLight};
  
  &:last-child {
    border-bottom: none;
  }

  .server-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .server-name {
    font-size: 12px;
    font-weight: 500;
    color: ${props => props.theme.colors.text};
  }

  .server-status {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
  }
`;

const StatusDot = styled.span`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: ${props => props.connected ? props.theme.colors.success : props.theme.colors.error};
`;

const HelpText = styled.div`
  font-size: 11px;
  color: ${props => props.theme.colors.textMuted};
  padding: 8px 12px;
  background: ${props => props.theme.colors.backgroundAlt};
  border-radius: 6px;
  margin-bottom: 12px;
  line-height: 1.5;
  
  strong {
    color: ${props => props.theme.colors.textSecondary};
  }
`;

const ToolsSelector = ({ chatService, selectedTools, onToolsChange, disabled }) => {
  const [tools, setTools] = useState([]);
  const [categories, setCategories] = useState([]);
  const [expandedCategories, setExpandedCategories] = useState(['local', 'mcp-local', 'mcp-remote']);
  const [isExpanded, setIsExpanded] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [toolCounts, setToolCounts] = useState({ local: 0, stdio: 0, sse: 0 });
  const [serverStatus, setServerStatus] = useState([]);

  useEffect(() => {
    loadTools();
  }, [chatService]);

  const loadTools = async () => {
    if (!chatService) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await chatService.getAllTools();
      if (response.success) {
        setTools(response.tools || []);
        setCategories(response.categories || []);
        setToolCounts({
          local: response.localCount || 0,
          stdio: response.mcpStdioCount || 0,
          sse: response.mcpSseCount || 0
        });
        setServerStatus(response.serverStatus || []);
      } else {
        setError(response.error || 'Failed to load tools');
      }
    } catch (err) {
      console.error('Failed to load tools:', err);
      setError(err.message || 'Failed to load tools');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleCategory = (categoryName) => {
    setExpandedCategories(prev => 
      prev.includes(categoryName)
        ? prev.filter(c => c !== categoryName)
        : [...prev, categoryName]
    );
  };

  const toggleTool = (tool) => {
    if (disabled) return;
    
    const toolId = tool.fullName || tool.name;
    const isSelected = selectedTools.some(t => (t.fullName || t.name) === toolId);
    
    if (isSelected) {
      onToolsChange(selectedTools.filter(t => (t.fullName || t.name) !== toolId));
    } else {
      onToolsChange([...selectedTools, {
        name: tool.name,
        fullName: tool.fullName,
        source: tool.source,
        serverName: tool.serverName,
        transport: tool.transport
      }]);
    }
  };

  const selectAllInCategory = (category) => {
    if (disabled) return;
    
    const categoryTools = category.tools || [];
    const allSelected = categoryTools.every(tool => 
      selectedTools.some(t => (t.fullName || t.name) === (tool.fullName || tool.name))
    );
    
    if (allSelected) {
      // Deselect all in category
      const toolIds = categoryTools.map(t => t.fullName || t.name);
      onToolsChange(selectedTools.filter(t => !toolIds.includes(t.fullName || t.name)));
    } else {
      // Select all in category
      const newTools = categoryTools.filter(tool => 
        !selectedTools.some(t => (t.fullName || t.name) === (tool.fullName || tool.name))
      ).map(tool => ({
        name: tool.name,
        fullName: tool.fullName,
        source: tool.source,
        serverName: tool.serverName,
        transport: tool.transport
      }));
      onToolsChange([...selectedTools, ...newTools]);
    }
  };

  const getCategoryIcon = (category) => {
    switch(category) {
      case 'local': return <Zap size={14} />;
      case 'mcp-local': 
      case 'mcp-stdio': return <Terminal size={14} />;
      case 'mcp-remote': 
      case 'mcp-sse': return <Wifi size={14} />;
      case 'mcp-bridge': return <Link2 size={14} />;
      default: return <Wrench size={14} />;
    }
  };

  const getTransportIcon = (transport) => {
    switch(transport) {
      case 'stdio': return <Terminal size={10} />;
      case 'sse':
      case 'http': return <Wifi size={10} />;
      case 'native': return <Zap size={10} />;
      default: return <Wrench size={10} />;
    }
  };

  const isToolSelected = (tool) => {
    const toolId = tool.fullName || tool.name;
    return selectedTools.some(t => (t.fullName || t.name) === toolId);
  };

  return (
    <ToolsContainer>
      <ToolsHeader onClick={() => setIsExpanded(!isExpanded)}>
        <h3>
          <Wrench size={16} />
          Tools
          {selectedTools.length > 0 && (
            <ToolsCount>{selectedTools.length} selected</ToolsCount>
          )}
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <RefreshButton 
            onClick={(e) => { e.stopPropagation(); loadTools(); }}
            className={isLoading ? 'loading' : ''}
            title="Refresh tools"
          >
            <RefreshCw size={14} />
          </RefreshButton>
          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </ToolsHeader>

      {isExpanded && (
        <>
          {/* Help text explaining tool types */}
          <HelpText>
            <strong>? Local:</strong> Native in-process tools (fastest)<br/>
            <strong>?? Local MCP:</strong> MCP tools via STDIO subprocess<br/>
            <strong>?? Remote MCP:</strong> MCP tools via SSE/HTTP server
          </HelpText>

          {/* Tool counts summary */}
          {!isLoading && tools.length > 0 && (
            <ToolsSummary>
              {toolCounts.local > 0 && (
                <SummaryBadge type="local">
                  <Zap size={10} />
                  {toolCounts.local} Local
                </SummaryBadge>
              )}
              {toolCounts.stdio > 0 && (
                <SummaryBadge type="stdio">
                  <Terminal size={10} />
                  {toolCounts.stdio} Local MCP
                </SummaryBadge>
              )}
              {toolCounts.sse > 0 && (
                <SummaryBadge type="sse">
                  <Wifi size={10} />
                  {toolCounts.sse} Remote MCP
                </SummaryBadge>
              )}
            </ToolsSummary>
          )}

          {error && <ErrorMessage>{error}</ErrorMessage>}
          
          {isLoading ? (
            <NoToolsMessage>Loading tools...</NoToolsMessage>
          ) : categories.length === 0 ? (
            <NoToolsMessage>No tools available. Start the MCP servers to see tools.</NoToolsMessage>
          ) : (
            categories.map(category => (
              <CategoryContainer key={category.name}>
                <CategoryHeader onClick={() => toggleCategory(category.name)}>
                  <div className="category-info">
                    <CategoryIcon category={category.name}>
                      {getCategoryIcon(category.name)}
                    </CategoryIcon>
                    <span className="category-name">{category.displayName}</span>
                    <span className="category-count">{category.count}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <SelectAllButton 
                      onClick={(e) => { e.stopPropagation(); selectAllInCategory(category); }}
                      disabled={disabled}
                    >
                      {category.tools?.every(t => isToolSelected(t)) ? 'Deselect All' : 'Select All'}
                    </SelectAllButton>
                    {expandedCategories.includes(category.name) 
                      ? <ChevronDown size={14} /> 
                      : <ChevronRight size={14} />
                    }
                  </div>
                </CategoryHeader>
                
                <ToolsList expanded={expandedCategories.includes(category.name)}>
                  {category.tools?.map(tool => (
                    <ToolItem 
                      key={tool.fullName || tool.name}
                      onClick={() => toggleTool(tool)}
                      className={isToolSelected(tool) ? 'selected' : ''}
                    >
                      <ToolCheckbox selected={isToolSelected(tool)}>
                        {isToolSelected(tool) && <Check size={12} />}
                      </ToolCheckbox>
                      <ToolInfo>
                        <div className="tool-header">
                          <span className="tool-name">{tool.name}</span>
                          {tool.transport && (
                            <TransportBadge transport={tool.transport}>
                              {tool.transport === 'native' ? 'LOCAL' : tool.transport.toUpperCase()}
                            </TransportBadge>
                          )}
                        </div>
                        <div className="tool-description">{tool.description}</div>
                        {tool.serverName && (
                          <div className="tool-source">
                            {getTransportIcon(tool.transport)}
                            <span>Server: {tool.serverName}</span>
                          </div>
                        )}
                      </ToolInfo>
                    </ToolItem>
                  ))}
                </ToolsList>
              </CategoryContainer>
            ))
          )}

          {/* Server Status */}
          {serverStatus.length > 0 && (
            <ServerStatusContainer>
              <ServerStatusHeader>MCP Server Status</ServerStatusHeader>
              {serverStatus.map(server => (
                <ServerStatusItem key={server.name}>
                  <div className="server-info">
                    {server.transport === 'stdio' ? <Terminal size={12} /> : <Wifi size={12} />}
                    <span className="server-name">{server.name}</span>
                    <TransportBadge transport={server.transport}>
                      {server.transport === 'stdio' ? 'LOCAL' : 'REMOTE'}
                    </TransportBadge>
                  </div>
                  <div className="server-status">
                    <StatusDot connected={server.isConnected} />
                    <span>{server.isConnected ? `${server.toolCount} tools` : 'Disconnected'}</span>
                  </div>
                </ServerStatusItem>
              ))}
            </ServerStatusContainer>
          )}
        </>
      )}
    </ToolsContainer>
  );
};

export default ToolsSelector;
