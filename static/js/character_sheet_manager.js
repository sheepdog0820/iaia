/**
 * Character Sheet Manager - Modular JavaScript for CoC 6th Edition
 * This module provides organized, maintainable code structure for character sheet functionality
 */

// ===================================
// Main Character Sheet Manager Class
// ===================================
class CharacterSheetManager {
    constructor() {
        // Sub-modules
        this.validation = new ValidationSystem();
        this.diceRoller = new DiceRoller();
        this.autoSave = new AutoSaveManager();
        this.progressTracker = new ProgressTracker();
        this.skillManager = new SkillManager();
        this.combatManager = new CombatManager();
        this.inventoryManager = new InventoryManager();
        this.backgroundManager = new BackgroundManager();
        this.growthManager = new GrowthManager();
        
        // Configuration
        this.config = {
            autoSaveInterval: 30000, // 30 seconds
            validationDelay: 500,    // 500ms delay for validation
            notificationDuration: 3000 // 3 seconds
        };
        
        // Initialize
        this.initialize();
    }
    
    initialize() {
        this.setupEventListeners();
        this.loadSavedData();
        this.initializeSubModules();
        this.updateAllCalculations();
    }
    
    loadSavedData() {
        // Load any saved draft data
        this.autoSave.loadDraft();
    }
    
    initializeSubModules() {
        // Initialize each sub-module
        // Add any specific initialization code here
    }
    
    updateAllCalculations() {
        // Update all derived calculations
        this.updateDerivedStats();
        this.progressTracker.update();
    }
    
    setupEventListeners() {
        // Global event delegation
        document.addEventListener('click', (e) => this.handleGlobalClick(e));
        document.addEventListener('input', (e) => this.handleGlobalInput(e));
        document.addEventListener('change', (e) => this.handleGlobalChange(e));
        
        // Form submission - DISABLED for 6th edition character creation
        // The template handles form submission properly via submitCharacterForm()
        console.log('[DEBUG] Character sheet manager: skipping form submit listener for 6th edition');
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }
    
    handleGlobalClick(event) {
        const target = event.target;
        
        // Dice roll buttons
        if (target.matches('.roll-ability-btn')) {
            this.diceRoller.rollAbility(target.dataset.ability);
        }
        
        // Save draft button
        if (target.matches('.save-draft-btn')) {
            this.autoSave.saveDraft();
        }
        
        // Add skill button
        if (target.matches('.add-skill-btn')) {
            this.skillManager.addCustomSkill();
        }
        
        // Remove buttons
        if (target.matches('.remove-btn')) {
            this.handleRemoveAction(target);
        }
    }
    
    handleGlobalInput(event) {
        const target = event.target;
        
        // Ability value changes
        if (target.matches('.ability-input')) {
            this.updateDerivedStats();
            this.progressTracker.update();
        }
        
        // Skill point allocation
        if (target.matches('.skill-points-input')) {
            this.skillManager.updateSkillTotal(target);
        }
        
        // Real-time validation
        if (target.hasAttribute('required')) {
            this.validation.validateField(target);
        }
    }
    
    handleGlobalChange(event) {
        const target = event.target;
        
        // Weight changes
        if (target.matches('[name*="weight"], [name*="quantity"]')) {
            this.inventoryManager.updateTotalWeight();
        }
        
        // Armor changes
        if (target.matches('[name*="armor_value"]')) {
            this.combatManager.updateArmorValue();
        }
    }
    
    handleKeyboardShortcuts(event) {
        // Ctrl/Cmd + S for save
        if ((event.ctrlKey || event.metaKey) && event.key === 's') {
            event.preventDefault();
            this.autoSave.saveDraft();
        }
        
        // Alt + Tab for section navigation
        if (event.altKey && event.key === 'Tab') {
            event.preventDefault();
            this.navigateToNextSection();
        }
    }
    
    async handleFormSubmit(event) {
        // Do NOT prevent default form submission for 6th edition character creation
        // The template has its own proper form submission handling
        console.log('[DEBUG] Character sheet manager: allowing default form submission');
        
        // Let the form submit naturally to /accounts/character/create/6th/
        // The template's submitCharacterForm() will handle validation and data preparation
        return true;
    }
    
    async saveCharacter(formData) {
        // Use the correct form submission instead of fetch API
        // The form should be submitted using the standard Django form
        console.log('[DEBUG] Character sheet manager: deferring to form submission');
        
        // Check if submitCharacterForm function exists and use it
        if (typeof window.submitCharacterForm === 'function') {
            console.log('[DEBUG] Using template submitCharacterForm function');
            window.submitCharacterForm();
            return Promise.resolve({ success: true });
        } else {
            console.error('[ERROR] submitCharacterForm function not found');
            throw new Error('Form submission function not available');
        }
    }
    
    handleSaveSuccess(response) {
        this.showNotification('保存が完了しました', 'success');
        // Additional success handling
    }
    
    handleSaveError(error) {
        this.showNotification('保存に失敗しました', 'error');
        console.error('Save error:', error);
    }
    
    handleRemoveAction(target) {
        // Handle various remove actions based on data attributes
        const action = target.dataset.action;
        
        switch(action) {
            case 'remove-skill':
                this.skillManager.removeSkill(target);
                break;
            case 'remove-item':
                this.inventoryManager.removeItem(target);
                break;
            case 'remove-growth':
                this.growthManager.removeRecord(target);
                break;
        }
    }
    
    navigateToNextSection() {
        const sections = document.querySelectorAll('.section');
        const currentSection = document.activeElement.closest('.section');
        const currentIndex = Array.from(sections).indexOf(currentSection);
        const nextSection = sections[(currentIndex + 1) % sections.length];
        
        if (nextSection) {
            nextSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            setTimeout(() => {
                nextSection.querySelector('input, select, textarea')?.focus();
            }, 300);
        }
    }
    
    updateDerivedStats() {
        // Update all derived statistics
        this.combatManager.updateCombatStats();
        this.inventoryManager.updateCarryCapacity();
        this.progressTracker.update();
    }
    
    showNotification(message, type = 'success') {
        const notification = new NotificationSystem();
        notification.show(message, type, this.config.notificationDuration);
    }
    
    showLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay') || this.createLoadingOverlay();
        overlay.style.display = 'flex';
    }
    
    hideLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
    
    createLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">保存中...</div>
        `;
        document.body.appendChild(overlay);
        return overlay;
    }
}

// ===================================
// Validation System
// ===================================
class ValidationSystem {
    constructor() {
        this.errors = new Map();
        this.validationRules = {
            required: (value) => value.trim() !== '',
            number: (value) => !isNaN(value) && value !== '',
            min: (value, min) => parseFloat(value) >= parseFloat(min),
            max: (value, max) => parseFloat(value) <= parseFloat(max),
            pattern: (value, pattern) => new RegExp(pattern).test(value)
        };
    }
    
    validateField(field) {
        const fieldName = field.name;
        const value = field.value;
        let isValid = true;
        let errorMessage = '';
        
        // Required validation
        if (field.hasAttribute('required') && !this.validationRules.required(value)) {
            isValid = false;
            errorMessage = 'この項目は必須です';
        }
        
        // Number validation
        else if (field.type === 'number' && value) {
            if (!this.validationRules.number(value)) {
                isValid = false;
                errorMessage = '数値を入力してください';
            } else {
                // Min/Max validation
                const min = field.getAttribute('min');
                const max = field.getAttribute('max');
                
                if (min && !this.validationRules.min(value, min)) {
                    isValid = false;
                    errorMessage = `${min}以上の値を入力してください`;
                }
                if (max && !this.validationRules.max(value, max)) {
                    isValid = false;
                    errorMessage = `${max}以下の値を入力してください`;
                }
            }
        }
        
        // Update UI
        if (isValid) {
            this.clearFieldError(field);
        } else {
            this.setFieldError(field, errorMessage);
        }
        
        return isValid;
    }
    
    validateForm() {
        let isValid = true;
        const requiredFields = document.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        if (!isValid) {
            this.showGlobalError('入力内容にエラーがあります。赤く表示された項目を確認してください。');
        }
        
        return isValid;
    }
    
    setFieldError(field, message) {
        field.classList.add('is-invalid');
        
        // Remove existing error message
        this.clearFieldError(field);
        
        // Add new error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        field.parentElement.appendChild(errorDiv);
        
        this.errors.set(field.name, message);
    }
    
    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentElement.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
        this.errors.delete(field.name);
    }
    
    showGlobalError(message) {
        const notification = new NotificationSystem();
        notification.show(message, 'error', 5000);
    }
}

// ===================================
// Dice Roller System
// ===================================
class DiceRoller {
    constructor() {
        this.diceSettings = this.loadDiceSettings();
    }
    
    loadDiceSettings() {
        // Load from current settings or defaults
        return window.currentDiceSettings || window.DEFAULT_DICE_SETTINGS;
    }
    
    rollAbility(ability) {
        const settings = this.diceSettings[ability];
        if (!settings) return 0;
        
        let total = 0;
        const rolls = [];
        
        // Roll dice
        for (let i = 0; i < settings.count; i++) {
            const roll = Math.floor(Math.random() * settings.sides) + 1;
            rolls.push(roll);
            total += roll;
        }
        
        // Add bonus
        total += settings.bonus;
        
        // Update UI
        this.updateAbilityValue(ability, total);
        this.showRollAnimation(ability, rolls, total);
        
        return total;
    }
    
    updateAbilityValue(ability, value) {
        const input = document.getElementById(ability);
        if (input) {
            input.value = value;
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
    
    showRollAnimation(ability, rolls, total) {
        const button = document.querySelector(`[data-ability="${ability}"]`);
        if (!button) return;
        
        // Disable button during animation
        button.disabled = true;
        const originalContent = button.innerHTML;
        
        // Show rolling animation
        button.innerHTML = '<i class="fas fa-dice fa-spin"></i>';
        button.classList.add('rolling');
        
        setTimeout(() => {
            // Show result
            button.innerHTML = `${total} (${rolls.join('+')})`;
            button.classList.remove('rolling');
            button.classList.add('flash-success');
            
            setTimeout(() => {
                // Restore original
                button.innerHTML = originalContent;
                button.disabled = false;
                button.classList.remove('flash-success');
            }, 2000);
        }, 500);
    }
}

// ===================================
// Auto Save Manager
// ===================================
class AutoSaveManager {
    constructor() {
        this.saveTimeout = null;
        this.lastSaveTime = null;
        this.isDirty = false;
        this.setupAutoSave();
    }
    
    setupAutoSave() {
        // Mark form as dirty on any input
        document.addEventListener('input', () => {
            this.isDirty = true;
            this.scheduleSave();
        });
        
        // Auto-save every 30 seconds if dirty
        setInterval(() => {
            if (this.isDirty) {
                this.saveDraft();
            }
        }, 30000);
        
        // Save before page unload
        window.addEventListener('beforeunload', (e) => {
            if (this.isDirty) {
                e.preventDefault();
                e.returnValue = '保存されていない変更があります。ページを離れますか？';
            }
        });
    }
    
    scheduleSave() {
        clearTimeout(this.saveTimeout);
        this.saveTimeout = setTimeout(() => this.saveDraft(), 5000);
    }
    
    async saveDraft() {
        if (!this.isDirty) return;
        
        const formData = this.collectFormData();
        
        try {
            // Save to localStorage
            localStorage.setItem('character_draft_6th', JSON.stringify(formData));
            this.isDirty = false;
            this.lastSaveTime = new Date();
            
            // Show notification
            this.showSaveNotification();
        } catch (error) {
            console.error('Draft save failed:', error);
        }
    }
    
    collectFormData() {
        const form = document.getElementById('character-form-6th');
        if (!form) return {};
        
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            if (data[key]) {
                // Handle multiple values
                if (!Array.isArray(data[key])) {
                    data[key] = [data[key]];
                }
                data[key].push(value);
            } else {
                data[key] = value;
            }
        }
        
        return data;
    }
    
    loadDraft() {
        const savedDraft = localStorage.getItem('character_draft_6th');
        if (!savedDraft) return;
        
        try {
            const data = JSON.parse(savedDraft);
            this.restoreFormData(data);
            
            const notification = new NotificationSystem();
            notification.show('下書きを復元しました', 'info');
        } catch (error) {
            console.error('Draft load failed:', error);
        }
    }
    
    restoreFormData(data) {
        Object.entries(data).forEach(([key, value]) => {
            const elements = document.querySelectorAll(`[name="${key}"]`);
            
            elements.forEach((element, index) => {
                // Skip file input fields for security reasons
                if (element.type === 'file') {
                    return;
                }
                
                if (element.type === 'checkbox' || element.type === 'radio') {
                    element.checked = value === element.value;
                } else if (Array.isArray(value)) {
                    element.value = value[index] || '';
                } else {
                    element.value = value;
                }
            });
        });
    }
    
    showSaveNotification() {
        const notification = new NotificationSystem();
        notification.show('下書きを保存しました', 'success', 2000);
    }
}

// ===================================
// Progress Tracker
// ===================================
class ProgressTracker {
    constructor() {
        this.sections = [
            { id: 'basic-info', weight: 20, required: ['name', 'age', 'occupation'] },
            { id: 'abilities', weight: 20, required: ['str', 'con', 'pow', 'dex', 'app', 'siz', 'int', 'edu'] },
            { id: 'skills', weight: 30, required: [] },
            { id: 'combat', weight: 10, required: [] },
            { id: 'inventory', weight: 10, required: [] },
            { id: 'background', weight: 10, required: [] }
        ];
    }
    
    update() {
        let totalProgress = 0;
        let completedSections = 0;
        
        this.sections.forEach(section => {
            const progress = this.calculateSectionProgress(section);
            totalProgress += progress * (section.weight / 100);
            
            if (progress === 100) {
                completedSections++;
            }
            
            // Update section indicator
            this.updateSectionIndicator(section.id, progress);
        });
        
        // Update main progress bar
        this.updateMainProgress(totalProgress, completedSections);
    }
    
    calculateSectionProgress(section) {
        const sectionElement = document.getElementById(section.id);
        if (!sectionElement) return 0;
        
        const inputs = sectionElement.querySelectorAll('input, textarea, select');
        const filled = Array.from(inputs).filter(input => {
            if (input.type === 'checkbox') return input.checked;
            if (input.type === 'radio') return input.checked;
            return input.value.trim() !== '';
        });
        
        const requiredFields = section.required.map(name => 
            sectionElement.querySelector(`[name="${name}"]`)
        ).filter(Boolean);
        
        const requiredFilled = requiredFields.filter(field => field.value.trim() !== '');
        
        if (requiredFields.length > 0) {
            return (requiredFilled.length / requiredFields.length) * 100;
        } else if (inputs.length > 0) {
            return (filled.length / inputs.length) * 100;
        }
        
        return 0;
    }
    
    updateSectionIndicator(sectionId, progress) {
        const indicator = document.querySelector(`[data-section="${sectionId}"] .section-progress`);
        if (indicator) {
            indicator.style.width = `${progress}%`;
            indicator.setAttribute('aria-valuenow', progress);
            
            // Update color based on progress
            if (progress === 100) {
                indicator.classList.remove('bg-warning', 'bg-danger');
                indicator.classList.add('bg-success');
            } else if (progress >= 50) {
                indicator.classList.remove('bg-success', 'bg-danger');
                indicator.classList.add('bg-warning');
            } else {
                indicator.classList.remove('bg-success', 'bg-warning');
                indicator.classList.add('bg-danger');
            }
        }
    }
    
    updateMainProgress(totalProgress, completedSections) {
        const progressBar = document.querySelector('.main-progress-bar');
        const progressText = document.querySelector('.progress-text');
        
        if (progressBar) {
            progressBar.style.width = `${totalProgress}%`;
            progressBar.setAttribute('aria-valuenow', totalProgress);
            progressBar.setAttribute('data-label', `${Math.round(totalProgress)}%完了`);
        }
        
        if (progressText) {
            progressText.textContent = `${completedSections}/${this.sections.length} セクション完了`;
        }
    }
}

// ===================================
// Notification System
// ===================================
class NotificationSystem {
    show(message, type = 'success', duration = 3000) {
        // Remove existing notifications
        this.removeExisting();
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} show`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
    
    getIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    removeExisting() {
        document.querySelectorAll('.notification').forEach(n => n.remove());
    }
}

// ===================================
// Additional Manager Classes
// ===================================

// Skill Manager
class SkillManager {
    constructor() {
        this.customSkills = this.loadCustomSkills();
    }
    
    loadCustomSkills() {
        const saved = localStorage.getItem('coc6th_custom_skills');
        return saved ? JSON.parse(saved) : [];
    }
    
    addCustomSkill() {
        // Implementation for adding custom skills
    }
    
    updateSkillTotal(input) {
        // Implementation for updating skill totals
    }
}

// Combat Manager
class CombatManager {
    updateCombatStats() {
        // Implementation for updating combat statistics
    }
    
    updateArmorValue() {
        // Implementation for updating armor values
    }
}

// Inventory Manager
class InventoryManager {
    updateTotalWeight() {
        // Implementation for updating total weight
    }
    
    updateCarryCapacity() {
        // Implementation for updating carry capacity
    }
}

// Background Manager
class BackgroundManager {
    generateRandom(type) {
        // Implementation for generating random backgrounds
    }
}

// Growth Manager
class GrowthManager {
    addRecord() {
        // Implementation for adding growth records
    }
    
    updateSummary() {
        // Implementation for updating growth summary
    }
}

// ===================================
// Initialize on DOM Ready
// ===================================
document.addEventListener('DOMContentLoaded', () => {
    // Initialize the character sheet manager
    window.characterSheetManager = new CharacterSheetManager();
    
    // Load draft if exists
    window.characterSheetManager.autoSave.loadDraft();
});

// ===================================
// Export for external use
// ===================================
window.CharacterSheetModules = {
    CharacterSheetManager,
    ValidationSystem,
    DiceRoller,
    AutoSaveManager,
    ProgressTracker,
    NotificationSystem,
    SkillManager,
    CombatManager,
    InventoryManager,
    BackgroundManager,
    GrowthManager
};