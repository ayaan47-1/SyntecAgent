import React, { useState, useEffect } from 'react';

const FIELD_LABELS = {
  module_name: 'Module Name',
  code: 'Code',
  description: 'Description',
  new_code: 'New Code',
  new_description: 'New Description',
};

const EDITABLE_FIELDS = {
  add_module: ['module_name', 'code', 'description'],
  update_module: ['new_code', 'new_description'],
  delete_module: [],
};

function ConfirmationModal({ pendingAction, onConfirm, onCancel, isConfirming }) {
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [editedParams, setEditedParams] = useState({});

  useEffect(() => {
    setIsSuggesting(false);
    setEditedParams({});
  }, [pendingAction]);

  if (!pendingAction) return null;

  const editableFields = EDITABLE_FIELDS[pendingAction.type] ?? [];
  const canSuggest = editableFields.length > 0;

  const handleSuggest = () => {
    setEditedParams({ ...pendingAction.params });
    setIsSuggesting(true);
  };

  const handleConfirm = () => {
    onConfirm(isSuggesting ? editedParams : pendingAction.params);
  };

  return (
    <div className="confirmation-overlay">
      <div className="confirmation-modal">
        <div className="confirmation-header">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <h3>Confirm Action</h3>
        </div>

        {!isSuggesting ? (
          <p className="confirmation-description">{pendingAction.description}</p>
        ) : (
          <div className="suggestion-form">
            {pendingAction.type === 'update_module' && (
              <div className="suggestion-field suggestion-field--readonly">
                <span className="suggestion-label">Module Name</span>
                <span className="suggestion-value">{pendingAction.params.module_name}</span>
              </div>
            )}
            {editableFields.map(field => (
              <div key={field} className="suggestion-field">
                <label className="suggestion-label" htmlFor={`sf-${field}`}>
                  {FIELD_LABELS[field] ?? field}
                </label>
                <input
                  id={`sf-${field}`}
                  className="suggestion-input"
                  value={editedParams[field] ?? ''}
                  onChange={e => setEditedParams(p => ({ ...p, [field]: e.target.value }))}
                  disabled={isConfirming}
                  autoComplete="off"
                />
              </div>
            ))}
          </div>
        )}

        <div className="confirmation-actions">
          <button className="confirm-btn cancel" onClick={onCancel} disabled={isConfirming}>
            Cancel
          </button>
          {!isSuggesting && canSuggest && (
            <button className="confirm-btn suggest" onClick={handleSuggest} disabled={isConfirming}>
              Suggest Changes
            </button>
          )}
          {isSuggesting && (
            <button className="confirm-btn suggest" onClick={() => setIsSuggesting(false)} disabled={isConfirming}>
              ← Back
            </button>
          )}
          <button className="confirm-btn confirm" onClick={handleConfirm} disabled={isConfirming}>
            {isConfirming ? 'Processing...' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmationModal;
