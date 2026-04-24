// Excel-like Spreadsheet Component
// Full Excel functionality with formulas, cell references, and grid navigation

class ExcelSpreadsheet {
    constructor(containerId, rows = 50, cols = 26) {
        this.container = document.getElementById(containerId);
        this.rows = rows;
        this.cols = cols;
        this.cells = {}; // Store cell data: { 'A1': { value: '100', formula: '=B1*2', display: '200' } }
        this.mergedCells = {}; // Store merged cell ranges: { 'A1': { colspan: 2, rowspan: 1 } }
        this.selectedCell = null;
        this.selectedRange = []; // For range selection
        this.isSelecting = false; // Track if user is dragging to select
        this.selectionStart = null; // Starting cell for drag selection
        this.formulaBar = null;
        this.init();
    }

    init() {
        this.render();
        this.setupEventListeners();
        this.loadSavedData();
    }

    // Render the spreadsheet
    render() {
        this.container.innerHTML = '';
        this.container.className = 'excel-container';

        // Create toolbar
        this.renderToolbar();

        // Create formula bar
        this.renderFormulaBar();

        // Create spreadsheet grid
        this.renderGrid();
    }

    // Render toolbar
    renderToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'excel-toolbar';
        toolbar.innerHTML = `
            <button type="button" class="btn btn-sm btn-outline-primary" onclick="excelSheet.addRow()" title="Add row under the selected cell (like Excel)">
                <i class="bi bi-plus"></i> Add row
            </button>
            <button type="button" class="btn btn-sm btn-outline-primary" onclick="excelSheet.addColumn()" title="Add column to the right of the selection">
                <i class="bi bi-plus"></i> Add column
            </button>
            <div class="toolbar-divider"></div>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="excelSheet.alignText('left')" title="Align Left">
                <i class="bi bi-text-left"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="excelSheet.alignText('center')" title="Align Center">
                <i class="bi bi-text-center"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="excelSheet.alignText('right')" title="Align Right">
                <i class="bi bi-text-right"></i>
            </button>
            <div class="toolbar-divider"></div>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="excelSheet.fillSelectionColor('#f1f3f4')" title="Subtle fill on selected cells">
                Shade
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="excelSheet.clearSelectionFill()" title="Clear background color in selection">
                Clear fill
            </button>
            <div class="toolbar-divider"></div>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="excelSheet.mergeCells()" title="Merge Cells">
                <i class="bi bi-border-outer"></i> Merge
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="excelSheet.unmergeCells()" title="Unmerge Cells">
                <i class="bi bi-border-inner"></i> Unmerge
            </button>
            <div class="toolbar-divider"></div>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="excelSheet.clearAll()" title="Clear All">
                <i class="bi bi-trash"></i> Clear
            </button>
            <button type="button" class="btn btn-sm btn-primary" onclick="excelSheet.saveData()" title="Save">
                <i class="bi bi-save"></i> Save
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="excelSheet.printSpreadsheet()" title="Print">
                <i class="bi bi-printer"></i> Print
            </button>
            <div class="toolbar-info">
                <span id="cell-info">No cell selected</span>
            </div>
        `;
        this.container.appendChild(toolbar);
    }

    // Render formula bar
    renderFormulaBar() {
        const formulaBarDiv = document.createElement('div');
        formulaBarDiv.className = 'excel-formula-bar';
        formulaBarDiv.innerHTML = `
            <label class="formula-label">fx</label>
            <input type="text" id="formula-input" class="formula-input" placeholder="Enter value or formula (e.g., =A1+B1, =SUMIFS(...), =XLOOKUP(...))">
        `;
        this.container.appendChild(formulaBarDiv);

        this.formulaBar = document.getElementById('formula-input');
        
        // Formula bar events
        this.formulaBar.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.updateCellFromFormulaBar();
            }
        });

        this.formulaBar.addEventListener('blur', () => {
            this.updateCellFromFormulaBar();
        });
    }

    // Render grid
    renderGrid() {
        const gridDiv = document.createElement('div');
        gridDiv.className = 'excel-grid';

        const table = document.createElement('table');
        table.className = 'excel-table';

        // Header row (A, B, C, ...)
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        // Empty corner cell
        const cornerTh = document.createElement('th');
        cornerTh.className = 'excel-corner';
        headerRow.appendChild(cornerTh);

        // Column headers with resize handles
        for (let col = 0; col < this.cols; col++) {
            const th = document.createElement('th');
            th.className = 'excel-col-header';
            th.dataset.col = col;
            
            const colName = this.getColumnName(col);
            th.innerHTML = `
                <span class="col-name">${colName}</span>
                <div class="col-resize-handle" data-col="${col}"></div>
            `;
            
            headerRow.appendChild(th);
        }
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Body rows
        const tbody = document.createElement('tbody');
        for (let row = 0; row < this.rows; row++) {
            const tr = document.createElement('tr');

            // Row header
            const rowTh = document.createElement('th');
            rowTh.className = 'excel-row-header';
            rowTh.dataset.row = row;
            rowTh.innerHTML = `
                <span class="row-name">${row + 1}</span>
                <div class="row-resize-handle" data-row="${row}"></div>
            `;
            tr.appendChild(rowTh);

            // Data cells
            for (let col = 0; col < this.cols; col++) {
                const cellRef = this.getCellReference(row, col);
                
                // Check if this cell is hidden by a merge
                if (this.isCellHidden(cellRef)) {
                    continue;
                }
                
                const td = document.createElement('td');
                td.className = 'excel-cell';
                td.dataset.col = col;
                td.dataset.cell = cellRef;
                td.dataset.row = row;
                td.dataset.col = col;

                // Apply merge if exists
                if (this.mergedCells[cellRef]) {
                    td.colSpan = this.mergedCells[cellRef].colspan || 1;
                    td.rowSpan = this.mergedCells[cellRef].rowspan || 1;
                    td.classList.add('merged-cell');
                }

                // Create input
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'cell-input';
                input.dataset.cell = cellRef;
                input.placeholder = ''; // All cells are editable

                // Load saved value - DISPLAY ONLY (not formula)
                if (this.cells[cellRef]) {
                    // Always prefer computed display, even when it is intentionally empty.
                    if (
                        Object.prototype.hasOwnProperty.call(this.cells[cellRef], 'display') &&
                        this.cells[cellRef].display !== null &&
                        this.cells[cellRef].display !== undefined
                    ) {
                        input.value = this.cells[cellRef].display;
                    } else {
                        input.value = this.cells[cellRef].value || '';
                    }
                    
                    // Mark formula cells visually but don't show formula in cell
                    if (this.cells[cellRef].formula) {
                        input.setAttribute('data-has-formula', 'true');
                        input.title = 'Formula: ' + this.cells[cellRef].formula + ' (Double-click to edit)';
                    }
                    
                    // Apply custom styling
                    if (this.cells[cellRef].style) {
                        input.classList.add('cell-style-' + this.cells[cellRef].style);
                    }
                    
                    // Apply text alignment
                    if (this.cells[cellRef].align) {
                        input.style.textAlign = this.cells[cellRef].align;
                    }
                    if (this.cells[cellRef].bgColor) {
                        input.style.backgroundColor = this.cells[cellRef].bgColor;
                    }
                }

                td.appendChild(input);
                tr.appendChild(td);
            }
            tbody.appendChild(tr);
        }
        table.appendChild(tbody);
        gridDiv.appendChild(table);
        this.container.appendChild(gridDiv);
        
        // Setup column resize functionality
        this.setupColumnResize();
        
        // Setup row resize functionality
        this.setupRowResize();
    }

    // Setup column resize functionality
    setupColumnResize() {
        const resizeHandles = this.container.querySelectorAll('.col-resize-handle');
        
        resizeHandles.forEach(handle => {
            let isResizing = false;
            let startX = 0;
            let startWidth = 0;
            let col = null;
            
            handle.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                isResizing = true;
                startX = e.pageX;
                col = parseInt(handle.dataset.col);
                
                // Get current width
                const th = handle.closest('th');
                startWidth = th.offsetWidth;
                
                // Add resizing class
                this.container.classList.add('is-resizing');
                
                // Mouse move handler
                const onMouseMove = (e) => {
                    if (!isResizing) return;
                    
                    const diff = e.pageX - startX;
                    const newWidth = Math.max(50, startWidth + diff); // Min width 50px
                    
                    // Apply width to all cells in this column
                    this.setColumnWidth(col, newWidth);
                };
                
                // Mouse up handler
                const onMouseUp = () => {
                    isResizing = false;
                    this.container.classList.remove('is-resizing');
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                };
                
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        });
    }

    // Set column width
    setColumnWidth(col, width) {
        // Set width for header
        const header = this.container.querySelector(`th.excel-col-header[data-col="${col}"]`);
        if (header) {
            header.style.width = width + 'px';
            header.style.minWidth = width + 'px';
        }
        
        // Set width for all cells in this column
        const cells = this.container.querySelectorAll(`td.excel-cell[data-col="${col}"]`);
        cells.forEach(cell => {
            cell.style.width = width + 'px';
            cell.style.minWidth = width + 'px';
        });
    }

    // Setup row resize functionality
    setupRowResize() {
        const resizeHandles = this.container.querySelectorAll('.row-resize-handle');
        
        resizeHandles.forEach(handle => {
            let isResizing = false;
            let startY = 0;
            let startHeight = 0;
            let row = null;
            
            handle.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                isResizing = true;
                startY = e.pageY;
                row = parseInt(handle.dataset.row);
                
                // Get current height
                const th = handle.closest('th');
                const tr = th.closest('tr');
                startHeight = tr.offsetHeight;
                
                // Add resizing classes
                this.container.classList.add('is-resizing', 'row-resizing');
                
                // Mouse move handler
                const onMouseMove = (e) => {
                    if (!isResizing) return;
                    
                    const diff = e.pageY - startY;
                    const newHeight = Math.max(25, startHeight + diff); // Min height 25px
                    
                    // Apply height to this row
                    this.setRowHeight(row, newHeight);
                };
                
                // Mouse up handler
                const onMouseUp = () => {
                    isResizing = false;
                    this.container.classList.remove('is-resizing', 'row-resizing');
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                };
                
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        });
    }

    // Set row height
    setRowHeight(row, height) {
        // Find the row in tbody (skip thead)
        const tbody = this.container.querySelector('tbody');
        const tr = tbody.querySelectorAll('tr')[row];
        
        if (tr) {
            tr.style.height = height + 'px';
            
            // Set height for all cells in this row
            const cells = tr.querySelectorAll('td, th');
            cells.forEach(cell => {
                cell.style.height = height + 'px';
            });
        }
    }

    // Setup event listeners (pointer events: works for mouse + tablet/touch)
    setupEventListeners() {
        if (this._excelListenersBound) {
            return;
        }
        this._excelListenersBound = true;

        const resolveInputFromTarget = (target) => {
            if (!target) return null;
            if (target.classList && target.classList.contains('cell-input')) {
                return target;
            }
            if (target.closest) {
                const td = target.closest('td.excel-cell');
                if (td) {
                    return td.querySelector('.cell-input');
                }
            }
            return null;
        };

        const endDragSelect = () => {
            if (this.isSelecting) {
                this.isSelecting = false;
                this.container.classList.remove('is-selecting');
            }
        };

        this.container.addEventListener('pointerdown', (e) => {
            const input = resolveInputFromTarget(e.target);
            if (input) {
                this.isSelecting = true;
                this.selectionStart = input;
                this.selectCell(input);
                this.container.classList.add('is-selecting');
            }
        });

        this.container.addEventListener('pointermove', (e) => {
            if (!this.isSelecting) return;
            const input = resolveInputFromTarget(e.target);
            if (input) {
                this.selectRange(this.selectionStart, input);
            }
        });

        this.container.addEventListener('focusin', (e) => {
            const input = resolveInputFromTarget(e.target);
            if (!input) {
                return;
            }
            if (this.isSelecting) {
                return;
            }
            this.selectCell(input);
        });

        document.addEventListener('pointerup', endDragSelect);
        document.addEventListener('pointercancel', endDragSelect);

        this.container.addEventListener('input', (e) => {
            if (e.target.classList.contains('cell-input')) {
                this.handleCellInput(e.target);
                // REAL-TIME COMPUTATION: Update all formulas immediately as you type
                // This makes it work exactly like Excel - instant updates
                this.recalculateAll();
            }
        });

        // Keyboard navigation
        this.container.addEventListener('keydown', (e) => {
            if (e.target.classList.contains('cell-input')) {
                this.handleKeyboardNavigation(e);
            }
        });

        // Double-click to edit formula (shows in formula bar, not in cell)
        this.container.addEventListener('dblclick', (e) => {
            if (e.target.classList.contains('cell-input')) {
                const cellRef = e.target.dataset.cell;
                if (this.cells[cellRef] && this.cells[cellRef].formula) {
                    // Show formula in formula bar
                    this.formulaBar.value = this.cells[cellRef].formula;
                    this.formulaBar.focus();
                    this.formulaBar.select();
                    
                    // Keep display value in cell (don't change it)
                    // Cell still shows the calculated result
                }
            }
        });
    }

    clearSelectionChrome() {
        if (!this.container) {
            return;
        }
        this.container.querySelectorAll('td.excel-cell').forEach((td) => {
            td.classList.remove('excel-cell--active', 'excel-cell--range', 'excel-cell--handle');
        });
    }

    // Select cell
    selectCell(input) {
        this.container.querySelectorAll('.cell-input').forEach((cell) => {
            cell.classList.remove('selected', 'range-selected');
        });
        this.clearSelectionChrome();

        input.classList.add('selected');
        this.selectedCell = input;
        this.selectedRange = [];

        const td = input.closest('td');
        if (td) {
            td.classList.add('excel-cell--active', 'excel-cell--handle');
        }

        // Update formula bar - show formula if exists, otherwise show value
        const cellRef = input.dataset.cell;
        if (this.cells[cellRef]) {
            // Show formula in formula bar (if it has one)
            this.formulaBar.value = this.cells[cellRef].formula || this.cells[cellRef].value || '';
        } else {
            this.formulaBar.value = input.value;
        }

        const cellInfo = document.getElementById('cell-info');
        if (cellInfo) {
            cellInfo.textContent = `Cell: ${cellRef}`;
        }
    }

    // Handle cell input - SMART COMPUTATION: automatically updates all dependent cells
    handleCellInput(input) {
        const cellRef = input.dataset.cell;
        const value = input.value;

        // Store value
        if (!this.cells[cellRef]) {
            this.cells[cellRef] = {};
        }

        if (value.startsWith('=')) {
            // It's a formula
            this.cells[cellRef].formula = value;
            this.cells[cellRef].value = value;
            this.evaluateFormula(cellRef);
            
            // Update input to show calculated value (not formula)
            input.value = this.cells[cellRef].display || '';
            input.setAttribute('data-has-formula', 'true');
            input.title = 'Formula: ' + value + ' (Double-click to edit)';
        } else {
            // It's a plain value
            this.cells[cellRef].value = value;
            this.cells[cellRef].formula = null;
            this.cells[cellRef].display = value;
            input.removeAttribute('data-has-formula');
            input.title = '';
        }

        // Update formula bar
        this.formulaBar.value = this.cells[cellRef].formula || value;

        // SMART COMPUTATION: Recalculate ALL dependent cells automatically
        // This makes the spreadsheet work like real Excel - change one cell, all connected cells update
        this.recalculateAll();

        // Silent auto-save (no notifications)
        this.saveData();
    }

    // Update cell from formula bar
    updateCellFromFormulaBar() {
        if (!this.selectedCell) return;

        const value = this.formulaBar.value;
        const cellRef = this.selectedCell.dataset.cell;
        
        if (!this.cells[cellRef]) {
            this.cells[cellRef] = {};
        }
        
        if (value.startsWith('=')) {
            // It's a formula
            this.cells[cellRef].formula = value;
            this.cells[cellRef].value = value;
            this.evaluateFormula(cellRef);
            
            // Display calculated value in cell (not formula)
            this.selectedCell.value = this.cells[cellRef].display || '#ERROR!';
            this.selectedCell.setAttribute('data-has-formula', 'true');
            this.selectedCell.title = 'Formula: ' + value + ' (Double-click to edit)';
        } else {
            // It's a plain value
            this.cells[cellRef].value = value;
            this.cells[cellRef].formula = null;
            this.cells[cellRef].display = value;
            this.selectedCell.value = value;
            this.selectedCell.removeAttribute('data-has-formula');
            this.selectedCell.title = '';
        }
        
        // Recalculate dependent cells
        this.recalculateAll();
        
        // Auto-save
        this.saveData();
    }

    // Evaluate formula
    evaluateFormula(cellRef) {
        const cell = this.cells[cellRef];
        if (!cell || !cell.formula) return;

        try {
            let formula = cell.formula.substring(1); // Remove '='
            
            // Check if formula contains only zeros or empty values
            // If so, leave cell empty instead of showing 0
            if (formula.match(/^0[\s\*\+\-\/]*0*$/)) {
                cell.display = '';
                const input = document.querySelector(`[data-cell="${cellRef}"]`);
                if (input) {
                    input.value = '';
                }
                return;
            }

            // Evaluate formula
            const result = this.evaluateExpression(formula);
            
            // Check if result is an error
            if (result === '#ERROR!' || result === 'NaN' || result === 'Infinity' || result === '-Infinity') {
                cell.display = '';
            } else if (result === 0 || result === '0') {
                // Only show result if it's not 0 from empty cells
                cell.display = '';
            } else {
                cell.display = result;
            }

            // Update display
            const input = document.querySelector(`[data-cell="${cellRef}"]`);
            if (input) {
                input.value = cell.display;
            }
        } catch (error) {
            console.error('Formula error in', cellRef, ':', error);
            cell.display = '';
            const input = document.querySelector(`[data-cell="${cellRef}"]`);
            if (input) {
                input.value = '';
            }
        }
    }

    // Replace cell references in formula
    replaceCellReferences(formula) {
        // Match references like A1, $A$1, A$1, $A1.
        const cellRefPattern = /(\$?[A-Z]+)(\$?\d+)/g;
        
        return formula.replace(cellRefPattern, (match, col, row, offset, whole) => {
            // Do not replace inside string literals like "A1".
            if (this._isInsideDoubleQuotes(whole, offset)) {
                return match;
            }
            const cleanCol = col.replace(/\$/g, '');
            const cleanRow = row.replace(/\$/g, '');
            const cellRef = cleanCol + cleanRow;
            return this.getCellNumericValue(cellRef);
        });
    }

    getCellNumericValue(cellRef) {
        const cell = this.cells[cellRef];
        if (!cell) return '0';
        if (cell.display !== undefined && cell.display !== null && cell.display !== '') {
            return this.parseLiteralNumber(cell.display);
        }
        if (cell.value !== undefined && cell.value !== null && cell.value !== '') {
            return this.parseLiteralNumber(cell.value);
        }
        return '0';
    }

    parseLiteralNumber(raw) {
        if (raw === null || raw === undefined || raw === '') return '0';
        const text = String(raw).trim();
        if (!text) return '0';

        // Convert percentages (e.g. 15% => 0.15)
        if (/%$/.test(text)) {
            const p = parseFloat(text.replace(/[,%\s]/g, ''));
            if (!isNaN(p)) return String(p / 100);
        }

        // Remove currency symbols, spaces, and thousand separators
        const numericText = text.replace(/[,\s₱$€£¥]/g, '');
        const n = parseFloat(numericText);
        return isNaN(n) ? '0' : String(n);
    }

    isCellReferenceToken(token) {
        return /^(\$?[A-Z]+)(\$?\d+)$/i.test((token || '').trim());
    }

    isRangeToken(token) {
        return /^(\$?[A-Z]+)(\$?\d+):(\$?[A-Z]+)(\$?\d+)$/i.test((token || '').trim());
    }

    _isInsideDoubleQuotes(text, index) {
        let inQuotes = false;
        for (let i = 0; i < index; i++) {
            if (text[i] === '"') {
                inQuotes = !inQuotes;
            }
        }
        return inQuotes;
    }

    splitFunctionArgs(argsString) {
        const out = [];
        let current = '';
        let depth = 0;
        let inQuotes = false;

        for (let i = 0; i < (argsString || '').length; i++) {
            const ch = argsString[i];
            if (ch === '"') {
                inQuotes = !inQuotes;
                current += ch;
                continue;
            }
            if (!inQuotes && ch === '(') {
                depth++;
                current += ch;
                continue;
            }
            if (!inQuotes && ch === ')') {
                depth = Math.max(0, depth - 1);
                current += ch;
                continue;
            }
            if (!inQuotes && depth === 0 && (ch === ',' || ch === ';')) {
                if (current.trim()) out.push(current.trim());
                current = '';
                continue;
            }
            current += ch;
        }
        if (current.trim()) out.push(current.trim());
        return out;
    }

    stripOuterQuotes(text) {
        const s = String(text || '').trim();
        if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) {
            return s.slice(1, -1);
        }
        return s;
    }

    getCellDisplayValue(cellRef) {
        const cell = this.cells[cellRef];
        if (!cell) return '';
        if (cell.display !== undefined && cell.display !== null) return String(cell.display);
        if (cell.value !== undefined && cell.value !== null) return String(cell.value);
        return '';
    }

    toNumber(value) {
        const n = parseFloat(this.parseLiteralNumber(value));
        return isNaN(n) ? 0 : n;
    }

    evaluateArg(token) {
        const t = String(token || '').trim();
        if (!t) return '';
        if (t.toUpperCase() === 'TRUE') return true;
        if (t.toUpperCase() === 'FALSE') return false;
        if (this.isCellReferenceToken(t)) {
            const ref = t.replace(/\$/g, '').toUpperCase();
            return this.getCellDisplayValue(ref);
        }
        if (this.isRangeToken(t)) {
            const [a, b] = t.split(':');
            return this.getCellRange(a.replace(/\$/g, '').toUpperCase(), b.replace(/\$/g, '').toUpperCase());
        }
        if (/^-?\d+(\.\d+)?$/.test(t)) return Number(t);
        if (t.startsWith('"') && t.endsWith('"')) return this.stripOuterQuotes(t);
        if (t.startsWith('=')) {
            return this.evaluateExpression(t.substring(1));
        }
        return t;
    }

    // Evaluate expression (supports improved Excel-like math and functions)
    evaluateExpression(expression) {
        expression = String(expression || '').trim();
        if (!expression) return '';

        // Excel exponent operator
        expression = expression.replace(/\^/g, '**');

        // Handle SUM function
        expression = this.handleSumFunction(expression);
        
        // Handle AVERAGE function
        expression = this.handleAverageFunction(expression);
        
        // Handle MIN function
        expression = this.handleMinFunction(expression);
        
        // Handle MAX function
        expression = this.handleMaxFunction(expression);
        
        // Handle COUNT function
        expression = this.handleCountFunction(expression);

        // Handle COUNTA function
        expression = this.handleCountAFunction(expression);

        // Additional statistical/math functions
        expression = this.handleMedianFunction(expression);
        expression = this.handleProductFunction(expression);
        expression = this.handleModFunction(expression);
        expression = this.handlePowerFunction(expression);
        expression = this.handleSqrtFunction(expression);

        // Criteria/range functions
        expression = this.handleSumIfFunction(expression);
        expression = this.handleCountIfFunction(expression);
        expression = this.handleSumIfsFunction(expression);
        expression = this.handleCountIfsFunction(expression);

        // Handle ABS function
        expression = this.handleAbsFunction(expression);

        // Handle ROUND function
        expression = this.handleRoundFunction(expression);

        // Text functions
        expression = this.handleLenFunction(expression);
        expression = this.handleLeftFunction(expression);
        expression = this.handleRightFunction(expression);
        expression = this.handleConcatFunction(expression);
        expression = this.handleUpperFunction(expression);
        expression = this.handleLowerFunction(expression);
        expression = this.handleTrimFunction(expression);

        // Date/lookup functions
        expression = this.handleTodayFunction(expression);
        expression = this.handleNowFunction(expression);
        expression = this.handleYearFunction(expression);
        expression = this.handleMonthFunction(expression);
        expression = this.handleDayFunction(expression);
        expression = this.handleVlookupFunction(expression);
        expression = this.handleXlookupFunction(expression);

        // Replace remaining standalone cell references (e.g., A1+B1).
        // Do this AFTER range functions so refs like D6:D7 are preserved for SUM.
        expression = this.replaceCellReferences(expression);
        
        // Handle IF function (basic support)
        expression = this.handleIfFunction(expression);

        // Logical helpers
        expression = this.handleAndFunction(expression);
        expression = this.handleOrFunction(expression);
        expression = this.handleNotFunction(expression);

        // Handle IFERROR function
        expression = this.handleIfErrorFunction(expression);

        try {
            // Use Function constructor for safe evaluation
            const result = new Function('return ' + expression)();

            // Keep text/boolean results as-is (Excel-like behavior)
            if (typeof result === 'string') {
                return result;
            }
            if (typeof result === 'boolean') {
                return result ? 'TRUE' : 'FALSE';
            }
            if (result === null || result === undefined || isNaN(result) || !isFinite(result)) {
                return '';
            }
            
            return this.formatNumber(result);
        } catch (error) {
            console.error('Expression evaluation error:', expression, error);
            return '';
        }
    }

    // Handle SUM function
    handleSumFunction(expression) {
        const sumPattern = /SUM\(([^)]+)\)/gi;
        return expression.replace(sumPattern, (match, args) => {
            const values = this.getFunctionArgValues(args);
            const sum = values.reduce((acc, val) => acc + this.toNumber(val), 0);
            return sum;
        });
    }

    // Handle AVERAGE function
    handleAverageFunction(expression) {
        const avgPattern = /AVERAGE\(([^)]+)\)/gi;
        return expression.replace(avgPattern, (match, args) => {
            const values = this.getFunctionArgValues(args);
            const sum = values.reduce((acc, val) => acc + this.toNumber(val), 0);
            const avg = values.length ? (sum / values.length) : 0;
            return avg;
        });
    }
    
    // Handle MIN function
    handleMinFunction(expression) {
        const minPattern = /MIN\(([^)]+)\)/gi;
        return expression.replace(minPattern, (match, args) => {
            const values = this.getFunctionArgValues(args);
            const numbers = values.map(v => this.toNumber(v)).filter(n => !isNaN(n));
            return numbers.length > 0 ? Math.min(...numbers) : 0;
        });
    }
    
    // Handle MAX function
    handleMaxFunction(expression) {
        const maxPattern = /MAX\(([^)]+)\)/gi;
        return expression.replace(maxPattern, (match, args) => {
            const values = this.getFunctionArgValues(args);
            const numbers = values.map(v => this.toNumber(v)).filter(n => !isNaN(n));
            return numbers.length > 0 ? Math.max(...numbers) : 0;
        });
    }
    
    // Handle COUNT function
    handleCountFunction(expression) {
        const countPattern = /COUNT\(([^)]+)\)/gi;
        return expression.replace(countPattern, (match, args) => {
            const values = this.getFunctionArgValues(args);
            const numbers = values.filter((v) => {
                const raw = String(v ?? '').trim();
                if (!raw) return false;
                const compact = raw.replace(/[,\s₱$€£¥]/g, '').replace(/%$/, '');
                return /^-?\d+(\.\d+)?$/.test(compact);
            });
            return numbers.length;
        });
    }

    // Handle COUNTA function
    handleCountAFunction(expression) {
        const countAPattern = /COUNTA\(([^)]+)\)/gi;
        return expression.replace(countAPattern, (match, args) => {
            const values = this.getFunctionArgValues(args);
            return values.filter(v => v !== null && v !== undefined && String(v).trim() !== '').length;
        });
    }

    // Handle ABS function
    handleAbsFunction(expression) {
        const absPattern = /ABS\(([^)]+)\)/gi;
        return expression.replace(absPattern, (match, arg) => {
            const n = parseFloat(arg);
            return isNaN(n) ? 0 : Math.abs(n);
        });
    }

    // Handle ROUND function: ROUND(number, decimals)
    handleRoundFunction(expression) {
        const roundPattern = /ROUND\(([^,]+),([^)]+)\)/gi;
        return expression.replace(roundPattern, (match, numExpr, decExpr) => {
            const n = this.toNumber(this.evaluateArg(numExpr));
            const d = parseInt(this.evaluateArg(decExpr), 10);
            if (isNaN(n)) return 0;
            const decimals = isNaN(d) ? 0 : d;
            return Number(n).toFixed(decimals);
        });
    }

    handleMedianFunction(expression) {
        const pattern = /MEDIAN\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, args) => {
            const nums = this.getFunctionArgValues(args).map(v => this.toNumber(v)).filter(v => !isNaN(v)).sort((a, b) => a - b);
            if (!nums.length) return 0;
            const mid = Math.floor(nums.length / 2);
            return nums.length % 2 ? nums[mid] : (nums[mid - 1] + nums[mid]) / 2;
        });
    }

    handleProductFunction(expression) {
        const pattern = /PRODUCT\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, args) => {
            const nums = this.getFunctionArgValues(args).map(v => this.toNumber(v)).filter(v => !isNaN(v));
            if (!nums.length) return 0;
            return nums.reduce((acc, n) => acc * n, 1);
        });
    }

    handleModFunction(expression) {
        const pattern = /MOD\(([^,]+),([^)]+)\)/gi;
        return expression.replace(pattern, (match, a, b) => {
            const n1 = this.toNumber(this.evaluateArg(a));
            const n2 = this.toNumber(this.evaluateArg(b));
            if (!n2) return 0;
            return n1 % n2;
        });
    }

    handlePowerFunction(expression) {
        const pattern = /POWER\(([^,]+),([^)]+)\)/gi;
        return expression.replace(pattern, (match, a, b) => {
            const base = this.toNumber(this.evaluateArg(a));
            const exp = this.toNumber(this.evaluateArg(b));
            return Math.pow(base, exp);
        });
    }

    handleSqrtFunction(expression) {
        const pattern = /SQRT\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, a) => {
            const n = this.toNumber(this.evaluateArg(a));
            return n < 0 ? 0 : Math.sqrt(n);
        });
    }

    // Supports function args like: A1:A10, A1, B2, 100, A1:B2, C5
    getFunctionArgValues(argsString) {
        const tokens = this.splitFunctionArgs(argsString);
        const values = [];

        tokens.forEach((token) => {
            const normalized = token.replace(/\$/g, '').toUpperCase();
            const rangeMatch = normalized.match(/^([A-Z]+\d+):([A-Z]+\d+)$/i);
            const cellMatch = normalized.match(/^([A-Z]+\d+)$/i);

            if (rangeMatch) {
                values.push(...this.getCellRange(rangeMatch[1].toUpperCase(), rangeMatch[2].toUpperCase()));
            } else if (cellMatch) {
                const ref = cellMatch[1].toUpperCase();
                const cell = this.cells[ref];
                values.push(cell ? (cell.display || cell.value || '') : '');
            } else {
                values.push(this.evaluateArg(token));
            }
        });

        return values;
    }

    _criteriaMatch(value, criteriaRaw) {
        const criteria = String(this.stripOuterQuotes(criteriaRaw || '')).trim();
        const text = String(value === null || value === undefined ? '' : value);
        const asNum = this.toNumber(value);

        const opMatch = criteria.match(/^(<=|>=|<>|=|<|>)(.*)$/);
        if (opMatch) {
            const op = opMatch[1];
            const rightRaw = opMatch[2].trim();
            const rightNum = parseFloat(this.parseLiteralNumber(rightRaw));
            const rightText = rightRaw;

            if (!isNaN(asNum) && !isNaN(rightNum)) {
                if (op === '<') return asNum < rightNum;
                if (op === '>') return asNum > rightNum;
                if (op === '<=') return asNum <= rightNum;
                if (op === '>=') return asNum >= rightNum;
                if (op === '=') return asNum === rightNum;
                if (op === '<>') return asNum !== rightNum;
            }
            if (op === '=') return text === rightText;
            if (op === '<>') return text !== rightText;
            if (op === '<') return text < rightText;
            if (op === '>') return text > rightText;
            if (op === '<=') return text <= rightText;
            if (op === '>=') return text >= rightText;
        }

        return text === criteria;
    }

    handleSumIfFunction(expression) {
        const pattern = /SUMIF\(([^,]+),([^,]+),([^)]+)\)/gi;
        return expression.replace(pattern, (match, rangeArg, criteriaArg, sumRangeArg) => {
            const rangeToken = String(rangeArg || '').trim().replace(/\$/g, '').toUpperCase();
            const sumToken = String(sumRangeArg || '').trim().replace(/\$/g, '').toUpperCase();
            if (!this.isRangeToken(rangeToken) || !this.isRangeToken(sumToken)) return 0;
            const [r1, r2] = rangeToken.split(':');
            const [s1, s2] = sumToken.split(':');
            const rangeVals = this.getCellRange(r1, r2);
            const sumVals = this.getCellRange(s1, s2);
            const len = Math.min(rangeVals.length, sumVals.length);
            let total = 0;
            for (let i = 0; i < len; i++) {
                if (this._criteriaMatch(rangeVals[i], criteriaArg)) {
                    total += this.toNumber(sumVals[i]);
                }
            }
            return total;
        });
    }

    handleCountIfFunction(expression) {
        const pattern = /COUNTIF\(([^,]+),([^)]+)\)/gi;
        return expression.replace(pattern, (match, rangeArg, criteriaArg) => {
            const rangeToken = String(rangeArg || '').trim().replace(/\$/g, '').toUpperCase();
            if (!this.isRangeToken(rangeToken)) return 0;
            const [r1, r2] = rangeToken.split(':');
            const rangeVals = this.getCellRange(r1, r2);
            return rangeVals.filter(v => this._criteriaMatch(v, criteriaArg)).length;
        });
    }

    handleSumIfsFunction(expression) {
        const pattern = /SUMIFS\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, args) => {
            const parts = this.splitFunctionArgs(args);
            if (parts.length < 3 || parts.length % 2 === 0) return 0;
            const sumToken = String(parts[0] || '').trim().replace(/\$/g, '').toUpperCase();
            if (!this.isRangeToken(sumToken)) return 0;
            const [s1, s2] = sumToken.split(':');
            const sumVals = this.getCellRange(s1, s2);

            const criteriaSets = [];
            for (let i = 1; i < parts.length; i += 2) {
                const rToken = String(parts[i] || '').trim().replace(/\$/g, '').toUpperCase();
                if (!this.isRangeToken(rToken)) return 0;
                const [a, b] = rToken.split(':');
                criteriaSets.push({
                    values: this.getCellRange(a, b),
                    criteria: parts[i + 1],
                });
            }

            let total = 0;
            for (let idx = 0; idx < sumVals.length; idx++) {
                const ok = criteriaSets.every(set => this._criteriaMatch(set.values[idx], set.criteria));
                if (ok) total += this.toNumber(sumVals[idx]);
            }
            return total;
        });
    }

    handleCountIfsFunction(expression) {
        const pattern = /COUNTIFS\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, args) => {
            const parts = this.splitFunctionArgs(args);
            if (parts.length < 2 || parts.length % 2 !== 0) return 0;
            const criteriaSets = [];
            for (let i = 0; i < parts.length; i += 2) {
                const rToken = String(parts[i] || '').trim().replace(/\$/g, '').toUpperCase();
                if (!this.isRangeToken(rToken)) return 0;
                const [a, b] = rToken.split(':');
                criteriaSets.push({
                    values: this.getCellRange(a, b),
                    criteria: parts[i + 1],
                });
            }
            const len = criteriaSets[0]?.values?.length || 0;
            let count = 0;
            for (let idx = 0; idx < len; idx++) {
                const ok = criteriaSets.every(set => this._criteriaMatch(set.values[idx], set.criteria));
                if (ok) count++;
            }
            return count;
        });
    }
    
    // Handle IF function - basic support: IF(condition, true_value, false_value)
    handleIfFunction(expression) {
        const ifPattern = /IF\(([^,]+),([^,]+),([^)]+)\)/gi;
        
        return expression.replace(ifPattern, (match, condition, trueVal, falseVal) => {
            try {
                // Evaluate condition
                const normalizedCondition = String(condition || '')
                    .replace(/(^|[^<>!=])=([^=])/g, '$1==$2');
                const condResult = new Function('return ' + normalizedCondition)();
                return condResult ? trueVal.trim() : falseVal.trim();
            } catch (e) {
                return 0;
            }
        });
    }

    // Handle IFERROR function: IFERROR(value, fallback)
    handleIfErrorFunction(expression) {
        const ifErrPattern = /IFERROR\(([^,]+),([^)]+)\)/gi;
        return expression.replace(ifErrPattern, (match, valueExpr, fallbackExpr) => {
            try {
                const result = new Function('return ' + valueExpr)();
                if (result === null || result === undefined || isNaN(result) || !isFinite(result)) {
                    return fallbackExpr.trim();
                }
                return result;
            } catch (e) {
                return fallbackExpr.trim();
            }
        });
    }

    handleLenFunction(expression) {
        const pattern = /LEN\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, arg) => {
            const value = this.evaluateArg(arg);
            return String(value ?? '').length;
        });
    }

    handleLeftFunction(expression) {
        const pattern = /LEFT\(([^,]+),([^)]+)\)/gi;
        return expression.replace(pattern, (match, textArg, nArg) => {
            const text = String(this.evaluateArg(textArg) ?? '');
            const n = Math.max(0, parseInt(this.evaluateArg(nArg), 10) || 0);
            return `"${text.substring(0, n)}"`;
        });
    }

    handleRightFunction(expression) {
        const pattern = /RIGHT\(([^,]+),([^)]+)\)/gi;
        return expression.replace(pattern, (match, textArg, nArg) => {
            const text = String(this.evaluateArg(textArg) ?? '');
            const n = Math.max(0, parseInt(this.evaluateArg(nArg), 10) || 0);
            return `"${text.substring(Math.max(0, text.length - n))}"`;
        });
    }

    handleConcatFunction(expression) {
        const pattern = /(CONCAT|CONCATENATE)\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, fn, args) => {
            const parts = this.splitFunctionArgs(args);
            const text = parts.map(p => this.evaluateArg(p)).map(v => String(v ?? '')).join('');
            return `"${text.replace(/"/g, '\\"')}"`;
        });
    }

    handleUpperFunction(expression) {
        const pattern = /UPPER\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, arg) => `"${String(this.evaluateArg(arg) ?? '').toUpperCase()}"`);
    }

    handleLowerFunction(expression) {
        const pattern = /LOWER\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, arg) => `"${String(this.evaluateArg(arg) ?? '').toLowerCase()}"`);
    }

    handleTrimFunction(expression) {
        const pattern = /TRIM\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, arg) => `"${String(this.evaluateArg(arg) ?? '').replace(/\s+/g, ' ').trim()}"`);
    }

    handleTodayFunction(expression) {
        const pattern = /TODAY\(\)/gi;
        return expression.replace(pattern, () => `"${new Date().toISOString().slice(0, 10)}"`);
    }

    handleNowFunction(expression) {
        const pattern = /NOW\(\)/gi;
        return expression.replace(pattern, () => `"${new Date().toISOString()}"`);
    }

    handleYearFunction(expression) {
        const pattern = /YEAR\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, arg) => {
            const d = new Date(String(this.evaluateArg(arg)));
            return isNaN(d.getTime()) ? 0 : d.getFullYear();
        });
    }

    handleMonthFunction(expression) {
        const pattern = /MONTH\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, arg) => {
            const d = new Date(String(this.evaluateArg(arg)));
            return isNaN(d.getTime()) ? 0 : (d.getMonth() + 1);
        });
    }

    handleDayFunction(expression) {
        const pattern = /DAY\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, arg) => {
            const d = new Date(String(this.evaluateArg(arg)));
            return isNaN(d.getTime()) ? 0 : d.getDate();
        });
    }

    _lookupFromRange(lookupValue, lookupRangeToken, returnRangeToken) {
        const lk = String(lookupRangeToken || '').trim().replace(/\$/g, '').toUpperCase();
        const rt = String(returnRangeToken || '').trim().replace(/\$/g, '').toUpperCase();
        if (!this.isRangeToken(lk) || !this.isRangeToken(rt)) return '';
        const [l1, l2] = lk.split(':');
        const [r1, r2] = rt.split(':');
        const lookupValues = this.getCellRange(l1, l2);
        const returnValues = this.getCellRange(r1, r2);
        const key = String(lookupValue ?? '');
        for (let i = 0; i < lookupValues.length; i++) {
            if (String(lookupValues[i] ?? '') === key) {
                return returnValues[i] ?? '';
            }
        }
        return '';
    }

    handleVlookupFunction(expression) {
        const pattern = /VLOOKUP\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, args) => {
            const parts = this.splitFunctionArgs(args);
            if (parts.length < 3) return '""';
            const lookupValue = this.evaluateArg(parts[0]);
            const tableToken = String(parts[1] || '').trim().replace(/\$/g, '').toUpperCase();
            const columnIndex = parseInt(this.evaluateArg(parts[2]), 10);
            if (!this.isRangeToken(tableToken) || isNaN(columnIndex) || columnIndex < 1) return '""';

            const [sRef, eRef] = tableToken.split(':');
            const startCol = this.getColumnIndex(sRef.match(/[A-Z]+/)[0]);
            const startRow = parseInt(sRef.match(/\d+/)[0], 10) - 1;
            const endCol = this.getColumnIndex(eRef.match(/[A-Z]+/)[0]);
            const endRow = parseInt(eRef.match(/\d+/)[0], 10) - 1;
            const targetCol = startCol + (columnIndex - 1);
            if (targetCol > endCol) return '""';

            for (let row = startRow; row <= endRow; row++) {
                const keyRef = this.getCellReference(row, startCol);
                const keyVal = this.getCellDisplayValue(keyRef);
                if (String(keyVal ?? '') === String(lookupValue ?? '')) {
                    const resultRef = this.getCellReference(row, targetCol);
                    const result = this.getCellDisplayValue(resultRef);
                    const asNum = parseFloat(this.parseLiteralNumber(result));
                    return isNaN(asNum) ? `"${String(result ?? '').replace(/"/g, '\\"')}"` : asNum;
                }
            }
            return '""';
        });
    }

    handleXlookupFunction(expression) {
        const pattern = /XLOOKUP\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, args) => {
            const parts = this.splitFunctionArgs(args);
            if (parts.length < 3) return '""';
            const lookupValue = this.evaluateArg(parts[0]);
            const lookupRange = parts[1];
            const returnRange = parts[2];
            const notFound = parts[3] !== undefined ? this.evaluateArg(parts[3]) : '';
            const result = this._lookupFromRange(lookupValue, lookupRange, returnRange);
            const finalValue = (result === '' || result === undefined || result === null) ? notFound : result;
            const asNum = parseFloat(this.parseLiteralNumber(finalValue));
            return isNaN(asNum)
                ? `"${String(finalValue ?? '').replace(/"/g, '\\"')}"`
                : asNum;
        });
    }

    handleAndFunction(expression) {
        const pattern = /AND\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, args) => {
            const vals = this.splitFunctionArgs(args).map(a => this.evaluateArg(a));
            const ok = vals.every(v => {
                if (typeof v === 'boolean') return v;
                if (typeof v === 'number') return v !== 0;
                return String(v).trim().toUpperCase() === 'TRUE' || String(v).trim() !== '';
            });
            return ok ? 'true' : 'false';
        });
    }

    handleOrFunction(expression) {
        const pattern = /OR\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, args) => {
            const vals = this.splitFunctionArgs(args).map(a => this.evaluateArg(a));
            const ok = vals.some(v => {
                if (typeof v === 'boolean') return v;
                if (typeof v === 'number') return v !== 0;
                return String(v).trim().toUpperCase() === 'TRUE';
            });
            return ok ? 'true' : 'false';
        });
    }

    handleNotFunction(expression) {
        const pattern = /NOT\(([^)]+)\)/gi;
        return expression.replace(pattern, (match, arg) => {
            const v = this.evaluateArg(arg);
            const boolVal = (typeof v === 'boolean')
                ? v
                : (typeof v === 'number' ? v !== 0 : String(v).trim().toUpperCase() === 'TRUE');
            return (!boolVal) ? 'true' : 'false';
        });
    }

    // Get cell range values
    getCellRange(startRef, endRef) {
        const startCol = this.getColumnIndex(startRef.match(/[A-Z]+/)[0]);
        const startRow = parseInt(startRef.match(/\d+/)[0]) - 1;
        const endCol = this.getColumnIndex(endRef.match(/[A-Z]+/)[0]);
        const endRow = parseInt(endRef.match(/\d+/)[0]) - 1;

        const values = [];
        for (let row = startRow; row <= endRow; row++) {
            for (let col = startCol; col <= endCol; col++) {
                const cellRef = this.getCellReference(row, col);
                const cell = this.cells[cellRef];
                if (cell) {
                    values.push(cell.display || cell.value || '0');
                }
            }
        }
        return values;
    }

    // Recalculate all formulas - SMART COMPUTATION ENGINE
    // This makes all cells connected - changing one cell automatically updates all dependent cells
    // Works exactly like real Excel
    recalculateAll() {
        // Multiple passes to handle dependencies (formulas that reference other formulas)
        // This ensures all cells are updated in the correct order
        const maxPasses = 5; // Prevent infinite loops
        
        for (let pass = 0; pass < maxPasses; pass++) {
            let hasChanges = false;
            
            Object.keys(this.cells).forEach(cellRef => {
                if (this.cells[cellRef].formula) {
                    const oldDisplay = this.cells[cellRef].display;
                    this.evaluateFormula(cellRef);
                    const newDisplay = this.cells[cellRef].display;
                    
                    // Check if value changed
                    if (oldDisplay !== newDisplay) {
                        hasChanges = true;
                    }
                }
            });
            
            // If no changes in this pass, we're done
            if (!hasChanges) {
                break;
            }
        }
    }

    // Keyboard navigation
    handleKeyboardNavigation(e) {
        if (!this.selectedCell) return;

        const row = parseInt(this.selectedCell.dataset.row);
        const col = parseInt(this.selectedCell.dataset.col);

        let newRow = row;
        let newCol = col;

        switch (e.key) {
            case 'ArrowUp':
                if (e.ctrlKey) {
                    e.preventDefault();
                    newRow = 0;
                    break;
                }
                e.preventDefault();
                newRow = Math.max(0, row - 1);
                break;
            case 'ArrowDown':
            case 'Enter':
                e.preventDefault();
                if (e.shiftKey) {
                    newRow = Math.max(0, row - 1);
                } else if (e.ctrlKey && e.key === 'ArrowDown') {
                    newRow = this.rows - 1;
                } else {
                    newRow = Math.min(this.rows - 1, row + 1);
                }
                break;
            case 'ArrowLeft':
                if (e.ctrlKey) {
                    e.preventDefault();
                    newCol = 0;
                    break;
                }
                if (e.target.selectionStart === 0) {
                    e.preventDefault();
                    newCol = Math.max(0, col - 1);
                }
                break;
            case 'ArrowRight':
                if (e.ctrlKey) {
                    e.preventDefault();
                    newCol = this.cols - 1;
                    break;
                }
                if (e.target.selectionStart === e.target.value.length) {
                    e.preventDefault();
                    newCol = Math.min(this.cols - 1, col + 1);
                }
                break;
            case 'Tab':
                e.preventDefault();
                if (e.shiftKey) {
                    newCol = Math.max(0, col - 1);
                } else {
                    newCol = Math.min(this.cols - 1, col + 1);
                }
                break;
            case 'Home':
                e.preventDefault();
                newCol = 0;
                break;
            case 'End':
                e.preventDefault();
                newCol = this.cols - 1;
                break;
            case 'F2':
                // Excel-like: edit selected formula/value in formula bar
                e.preventDefault();
                if (this.formulaBar) {
                    this.formulaBar.focus();
                    this.formulaBar.select();
                }
                return;
        }

        if (newRow !== row || newCol !== col) {
            const newCellRef = this.getCellReference(newRow, newCol);
            const newInput = document.querySelector(`[data-cell="${newCellRef}"]`);
            if (newInput) {
                newInput.focus();
                this.selectCell(newInput);
            }
        }
    }

    // Get column name (A, B, C, ..., Z, AA, AB, ...)
    getColumnName(index) {
        let name = '';
        while (index >= 0) {
            name = String.fromCharCode(65 + (index % 26)) + name;
            index = Math.floor(index / 26) - 1;
        }
        return name;
    }

    // Get column index from name
    getColumnIndex(name) {
        let index = 0;
        for (let i = 0; i < name.length; i++) {
            index = index * 26 + (name.charCodeAt(i) - 64);
        }
        return index - 1;
    }
    
    // Helper aliases for consistency
    columnToIndex(name) {
        return this.getColumnIndex(name);
    }
    
    indexToColumn(index) {
        return this.getColumnName(index);
    }

    // Get cell reference (e.g., A1, B2)
    getCellReference(row, col) {
        return this.getColumnName(col) + (row + 1);
    }

    // Format number
    formatNumber(num) {
        if (num === null || num === undefined || num === '' || isNaN(num) || !isFinite(num)) {
            return '';
        }
        // Format with 2 decimal places if needed, remove trailing zeros
        const formatted = Number(num).toFixed(2).replace(/\.?0+$/, '');
        return formatted;
    }

    // Add row — inserts a new row directly *below* the selected row (like Excel).
    // If no cell is selected, inserts below the first row (not at the bottom).
    addRow() {
        const selectedRow0 = this.selectedCell
            ? parseInt(this.selectedCell.dataset.row, 10)
            : 0;
        const selCol = this.selectedCell
            ? parseInt(this.selectedCell.dataset.col, 10)
            : 0;
        // 1-based index of the row to insert *after* (insert below this row in the grid)
        const Rsel = selectedRow0 + 1;

        const newCells = {};
        Object.keys(this.cells).forEach((cellRef) => {
            const match = cellRef.match(/([A-Z]+)(\d+)/);
            if (!match) {
                newCells[cellRef] = this.cells[cellRef];
                return;
            }
            const col = match[1];
            const row1 = parseInt(match[2], 10);
            if (row1 > Rsel) {
                newCells[col + (row1 + 1)] = this.cells[cellRef];
            } else {
                newCells[cellRef] = this.cells[cellRef];
            }
        });
        this.cells = newCells;

        const newMerged = {};
        Object.keys(this.mergedCells).forEach((cellRef) => {
            const match = cellRef.match(/([A-Z]+)(\d+)/);
            if (!match) {
                newMerged[cellRef] = this.mergedCells[cellRef];
                return;
            }
            const col = match[1];
            const row1 = parseInt(match[2], 10);
            if (row1 > Rsel) {
                newMerged[col + (row1 + 1)] = this.mergedCells[cellRef];
            } else {
                newMerged[cellRef] = this.mergedCells[cellRef];
            }
        });
        this.mergedCells = newMerged;

        this.rows++;
        this.render();
        this.recalculateAll();
        this.saveData();

        const newRow0 = selectedRow0 + 1;
        const newRef = this.getCellReference(newRow0, selCol);
        requestAnimationFrame(() => {
            const inp = this.container.querySelector(`.cell-input[data-cell="${newRef}"]`);
            if (inp) {
                this.selectCell(inp);
                try {
                    inp.focus({ preventScroll: true });
                } catch (e) {
                    inp.focus();
                }
            }
        });
    }

    // Add column — inserts a new column to the *right* of the selected column (like Excel)
    addColumn() {
        const sc = this.selectedCell
            ? parseInt(this.selectedCell.dataset.col, 10)
            : 0;

        const newCells = {};
        Object.keys(this.cells).forEach((cellRef) => {
            const match = cellRef.match(/([A-Z]+)(\d+)/);
            if (!match) {
                newCells[cellRef] = this.cells[cellRef];
                return;
            }
            const colName = match[1];
            const rowNum = match[2];
            const colIndex = this.columnToIndex(colName);
            if (colIndex > sc) {
                const newCol = this.indexToColumn(colIndex + 1);
                newCells[newCol + rowNum] = this.cells[cellRef];
            } else {
                newCells[cellRef] = this.cells[cellRef];
            }
        });
        this.cells = newCells;

        const newMerged = {};
        Object.keys(this.mergedCells).forEach((cellRef) => {
            const match = cellRef.match(/([A-Z]+)(\d+)/);
            if (!match) {
                newMerged[cellRef] = this.mergedCells[cellRef];
                return;
            }
            const colName = match[1];
            const rowNum = match[2];
            const colIndex = this.columnToIndex(colName);
            if (colIndex > sc) {
                const newCol = this.indexToColumn(colIndex + 1);
                newMerged[newCol + rowNum] = this.mergedCells[cellRef];
            } else {
                newMerged[cellRef] = this.mergedCells[cellRef];
            }
        });
        this.mergedCells = newMerged;

        this.cols++;
        this.render();
        this.recalculateAll();
        this.saveData();
    }

    /**
     * Apply background color to the current range selection (or single selected cell).
     * Colors persist in cell data for printing/export.
     */
    fillSelectionColor(color) {
        const refs = this.selectedRange.length > 0
            ? [...this.selectedRange]
            : (this.selectedCell ? [this.selectedCell.dataset.cell] : []);
        if (refs.length === 0) {
            const n = document.createElement('div');
            n.className = 'excel-notification';
            n.textContent = 'Select cells (click and drag) or one cell, then pick a color.';
            n.style.cssText = 'position: fixed; top: 80px; right: 20px; background: #6c757d; color: #fff; padding: 10px 20px; border-radius: 5px; z-index: 9999;';
            document.body.appendChild(n);
            setTimeout(() => n.remove(), 2000);
            return;
        }
        refs.forEach((cellRef) => {
            if (!this.cells[cellRef]) this.cells[cellRef] = {};
            this.cells[cellRef].bgColor = color;
            const input = this.container.querySelector(`[data-cell="${cellRef}"]`);
            if (input) input.style.backgroundColor = color;
        });
        this.saveData();
    }

    clearSelectionFill() {
        const refs = this.selectedRange.length > 0
            ? [...this.selectedRange]
            : (this.selectedCell ? [this.selectedCell.dataset.cell] : []);
        if (refs.length === 0) return;
        refs.forEach((cellRef) => {
            if (this.cells[cellRef]) {
                delete this.cells[cellRef].bgColor;
            }
            const input = this.container.querySelector(`[data-cell="${cellRef}"]`);
            if (input) input.style.backgroundColor = '';
        });
        this.saveData();
    }

    // Align text in selected cells
    alignText(alignment) {
        if (this.selectedRange.length > 0) {
            // Align all cells in range
            this.selectedRange.forEach(cellRef => {
                const input = document.querySelector(`[data-cell="${cellRef}"]`);
                if (input) {
                    input.style.textAlign = alignment;
                    
                    // Store alignment in cell data
                    if (!this.cells[cellRef]) {
                        this.cells[cellRef] = {};
                    }
                    this.cells[cellRef].align = alignment;
                }
            });
        } else if (this.selectedCell) {
            // Align single selected cell
            const cellRef = this.selectedCell.dataset.cell;
            this.selectedCell.style.textAlign = alignment;
            
            // Store alignment in cell data
            if (!this.cells[cellRef]) {
                this.cells[cellRef] = {};
            }
            this.cells[cellRef].align = alignment;
        } else {
            console.log('Please select a cell or range to align');
            // Show a subtle visual feedback instead of alert
            const notification = document.createElement('div');
            notification.className = 'excel-notification';
            notification.textContent = 'Select a cell to align text';
            notification.style.cssText = 'position: fixed; top: 80px; right: 20px; background: #17a2b8; color: #fff; padding: 10px 20px; border-radius: 5px; z-index: 9999; box-shadow: 0 2px 10px rgba(0,0,0,0.2);';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 2000);
            return;
        }
        
        // Silent save - no notifications
        this.saveData();
        console.log(`Text aligned: ${alignment}`);
    }

    // Clear all
    clearAll() {
        if (confirm('Clear all data? This cannot be undone.')) {
            this.cells = {};
            this.mergedCells = {};
            this.render();
            this.saveData();
        }
    }

    // Save data (silent background save)
    saveData() {
        const data = {
            rows: this.rows,
            cols: this.cols,
            cells: this.cells,
            mergedCells: this.mergedCells
        };
        // Silent save to sessionStorage - no notifications or submissions
        sessionStorage.setItem('excel_data', JSON.stringify(data));
    }

    // Load saved data
    loadSavedData() {
        const saved = sessionStorage.getItem('excel_data');
        if (saved) {
            try {
                const data = JSON.parse(saved);
                this.rows = data.rows || this.rows;
                this.cols = data.cols || this.cols;
                this.cells = data.cells || {};
                this.mergedCells = data.mergedCells || {};
                this.recalculateAll();
            } catch (e) {
                console.error('Error loading saved data:', e);
            }
        }
    }

    // Export to JSON
    exportData() {
        return {
            cells: this.cells,
            rows: this.rows,
            cols: this.cols,
            mergedCells: this.mergedCells
        };
    }

    // Import from JSON
    importData(data) {
        this.cells = data.cells || {};
        this.rows = data.rows || this.rows;
        this.cols = data.cols || this.cols;
        this.mergedCells = data.mergedCells || {};
        this.render();
        this.recalculateAll();
    }

    // Load pre-defined templates
    loadTemplate(templateName) {
        if (confirm('Load template? This will clear current data.')) {
            this.cells = {};
            
            if (templateName === 'sari_sari') {
                this.loadSariSariTemplate();
            } else if (templateName === 'hollow_blocks') {
                this.loadHollowBlocksTemplate();
            }
            
            this.render();
            this.recalculateAll();
            this.saveData();
        }
    }

    // Sari-Sari Store Template
    loadSariSariTemplate() {
        // Merge and set header
        this.mergedCells['A1'] = { colspan: 4, rowspan: 1 };
        this.setCellValue('A1', 'NENE SARI SARI STORE');
        
        this.mergedCells['A2'] = { colspan: 4, rowspan: 1 };
        this.setCellValue('A2', 'CASH FLOW STATEMENT');
        
        // SALES Section Header (merged)
        this.mergedCells['A4'] = { colspan: 4, rowspan: 1 };
        this.setCellValue('A4', 'SALES');
        
        // Column headers
        this.setCellValue('A5', 'PRODUCT');
        this.setCellValue('B5', 'Qty/Month');
        this.setCellValue('C5', 'Unit Price');
        this.setCellValue('D5', 'Monthly Sales');
        
        // Product rows (labels only, values blank)
        const products = [
            'Softdrinks', 'Cigarettes', 'Candies', 'Biscuits', 'Noodles',
            'Coffee', 'Sugar', 'Rice', 'Cooking Oil', 'Soap'
        ];
        
        products.forEach((product, index) => {
            const row = 6 + index;
            this.setCellValue(`A${row}`, product);
            // B, C columns left blank for CI to fill
            // D column has formula
            this.setCellValue(`D${row}`, `=B${row}*C${row}`);
        });
        
        // Total Sales (merged label)
        const totalRow = 6 + products.length;
        this.mergedCells[`A${totalRow}`] = { colspan: 3, rowspan: 1 };
        this.setCellValue(`A${totalRow}`, 'TOTAL SALES');
        this.setCellValue(`D${totalRow}`, `=SUM(D6:D${totalRow - 1})`);
        
        // Cost of Goods Sold (merged label)
        const cogsRow = totalRow + 1;
        this.mergedCells[`A${cogsRow}`] = { colspan: 3, rowspan: 1 };
        this.setCellValue(`A${cogsRow}`, 'COST OF GOODS SOLD (80%)');
        this.setCellValue(`D${cogsRow}`, `=D${totalRow}*0.8`);
        
        // Gross Sales (merged label)
        const grossRow = cogsRow + 1;
        this.mergedCells[`A${grossRow}`] = { colspan: 3, rowspan: 1 };
        this.setCellValue(`A${grossRow}`, 'GROSS SALES');
        this.setCellValue(`D${grossRow}`, `=D${totalRow}-D${cogsRow}`);
        
        // OTHER BUSINESS Section (merged header)
        const otherBusinessRow = grossRow + 2;
        this.mergedCells[`A${otherBusinessRow}`] = { colspan: 4, rowspan: 1 };
        this.setCellValue(`A${otherBusinessRow}`, 'OTHER BUSINESS');
        
        this.mergedCells[`A${otherBusinessRow + 1}`] = { colspan: 2, rowspan: 1 };
        this.setCellValue(`A${otherBusinessRow + 1}`, 'Business Name:');
        this.mergedCells[`C${otherBusinessRow + 1}`] = { colspan: 2, rowspan: 1 };
        
        this.mergedCells[`A${otherBusinessRow + 2}`] = { colspan: 2, rowspan: 1 };
        this.setCellValue(`A${otherBusinessRow + 2}`, 'Monthly Income:');
        this.mergedCells[`C${otherBusinessRow + 2}`] = { colspan: 2, rowspan: 1 };
        
        // OPERATING EXPENSES Section (merged header)
        const expensesStartRow = otherBusinessRow + 4;
        this.mergedCells[`A${expensesStartRow}`] = { colspan: 4, rowspan: 1 };
        this.setCellValue(`A${expensesStartRow}`, 'OPERATING EXPENSES');
        
        const expenses = [
            'Electric Bill', 'Water Bill', 'Fuel/Transportation',
            'House Rental', 'Food', 'Education', 'Miscellaneous'
        ];
        
        expenses.forEach((expense, index) => {
            const row = expensesStartRow + 1 + index;
            this.mergedCells[`A${row}`] = { colspan: 3, rowspan: 1 };
            this.setCellValue(`A${row}`, expense);
            // D column left blank for amount
        });
        
        // Total Operating Expenses (merged label)
        const totalExpRow = expensesStartRow + 1 + expenses.length;
        this.mergedCells[`A${totalExpRow}`] = { colspan: 3, rowspan: 1 };
        this.setCellValue(`A${totalExpRow}`, 'TOTAL OPERATING EXPENSES');
        this.setCellValue(`D${totalExpRow}`, `=SUM(D${expensesStartRow + 1}:D${totalExpRow - 1})`);
        
        // Gross Profit (merged label)
        const profitRow = totalExpRow + 1;
        this.mergedCells[`A${profitRow}`] = { colspan: 3, rowspan: 1 };
        this.setCellValue(`A${profitRow}`, 'GROSS PROFIT');
        this.setCellValue(`D${profitRow}`, `=D${grossRow}+C${otherBusinessRow + 2}-D${totalExpRow}`);
        
        // Set column widths
        setTimeout(() => {
            this.setColumnWidth(0, 200); // Column A - wider for labels
            this.setColumnWidth(1, 100); // Column B
            this.setColumnWidth(2, 100); // Column C
            this.setColumnWidth(3, 120); // Column D
        }, 100);
    }

    // Hollow Blocks / Sand & Gravel Template
    loadHollowBlocksTemplate() {
        // Header (merged)
        this.mergedCells['A1'] = { colspan: 3, rowspan: 1 };
        this.setCellValue('A1', 'SOURCES OF INCOME');
        
        // Column headers
        this.setCellValue('A2', 'Description');
        this.setCellValue('B2', 'Weekly');
        this.setCellValue('C2', 'Monthly');
        
        // Hollow Blocks Section Header (merged)
        this.mergedCells['A3'] = { colspan: 3, rowspan: 1 };
        this.setCellValue('A3', 'HOLLOW BLOCKS PRODUCTION');
        
        this.setCellValue('A4', 'Units Produced/Week:');
        this.setCellValue('A5', 'Price per Unit:');
        this.setCellValue('A6', 'Weekly Income:');
        this.setCellValue('B6', '=B4*B5');
        this.setCellValue('C6', '=B6*4');
        
        // Sand & Gravel Section Header (merged)
        this.mergedCells['A8'] = { colspan: 3, rowspan: 1 };
        this.setCellValue('A8', 'SAND & GRAVEL SALES');
        
        this.setCellValue('A9', 'Trips/Week:');
        this.setCellValue('A10', 'Price per Trip:');
        this.setCellValue('A11', 'Weekly Income:');
        this.setCellValue('B11', '=B9*B10');
        this.setCellValue('C11', '=B11*4');
        
        // Other Income Section Header (merged)
        this.mergedCells['A13'] = { colspan: 3, rowspan: 1 };
        this.setCellValue('A13', 'OTHER INCOME');
        
        this.setCellValue('A14', 'Source:');
        this.setCellValue('A15', 'Weekly Amount:');
        this.setCellValue('C15', '=B15*4');
        
        // Total Income (merged label)
        this.mergedCells['A17'] = { colspan: 2, rowspan: 1 };
        this.setCellValue('A17', 'TOTAL MONTHLY INCOME');
        this.setCellValue('C17', '=C6+C11+C15');
        
        // OPERATING EXPENSES Header (merged)
        this.mergedCells['A19'] = { colspan: 3, rowspan: 1 };
        this.setCellValue('A19', 'OPERATING EXPENSES');
        
        this.setCellValue('A20', 'Description');
        this.setCellValue('B20', 'Weekly');
        this.setCellValue('C20', 'Monthly');
        
        const expenses = [
            'Raw Materials (Cement, Sand)',
            'Labor/Wages',
            'Fuel/Transportation',
            'Equipment Maintenance',
            'Electric Bill',
            'Water Bill',
            'Food/Household',
            'Education',
            'Miscellaneous'
        ];
        
        expenses.forEach((expense, index) => {
            const row = 21 + index;
            this.setCellValue(`A${row}`, expense);
            this.setCellValue(`C${row}`, `=B${row}*4`);
        });
        
        // Total Operating Expenses (merged label)
        const totalExpRow = 21 + expenses.length;
        this.mergedCells[`A${totalExpRow}`] = { colspan: 2, rowspan: 1 };
        this.setCellValue(`A${totalExpRow}`, 'TOTAL OPERATING EXPENSES');
        this.setCellValue(`C${totalExpRow}`, `=SUM(C21:C${totalExpRow - 1})`);
        
        // Net Income (merged label)
        const netRow = totalExpRow + 1;
        this.mergedCells[`A${netRow}`] = { colspan: 2, rowspan: 1 };
        this.setCellValue(`A${netRow}`, 'NET MONTHLY INCOME');
        this.setCellValue(`C${netRow}`, `=C17-C${totalExpRow}`);
        
        // Debt Service Capacity (merged label)
        const debtRow = netRow + 2;
        this.mergedCells[`A${debtRow}`] = { colspan: 2, rowspan: 1 };
        this.setCellValue(`A${debtRow}`, 'DEBT SERVICE CAPACITY (70%)');
        this.setCellValue(`C${debtRow}`, `=C${netRow}*0.7`);
        
        // Set column widths
        setTimeout(() => {
            this.setColumnWidth(0, 250); // Column A - wider for descriptions
            this.setColumnWidth(1, 100); // Column B
            this.setColumnWidth(2, 120); // Column C
        }, 100);
    }

    // Helper method to set cell value
    setCellValue(cellRef, value) {
        if (!this.cells[cellRef]) {
            this.cells[cellRef] = {};
        }
        
        if (value.startsWith('=')) {
            this.cells[cellRef].formula = value;
            this.cells[cellRef].value = value;
            this.cells[cellRef].display = ''; // Leave empty until evaluated
            // Don't evaluate immediately - will be done by recalculateAll()
        } else {
            this.cells[cellRef].value = value;
            this.cells[cellRef].display = value;
            this.cells[cellRef].formula = null;
        }
        
        // Apply styling based on content
        this.applyCellStyling(cellRef, value);
    }

    // Apply styling to cells based on content
    applyCellStyling(cellRef, value) {
        if (!this.cells[cellRef]) return;
        
        const upperValue = value.toString().toUpperCase();
        
        // Header styling
        if (upperValue.includes('CASH FLOW') || 
            upperValue.includes('SOURCES OF INCOME') ||
            upperValue.includes('STATEMENT')) {
            this.cells[cellRef].style = 'header-main';
        }
        // Section header styling
        else if (upperValue.includes('SALES') || 
                 upperValue.includes('OPERATING EXPENSES') ||
                 upperValue.includes('OTHER BUSINESS') ||
                 upperValue.includes('PRODUCTION') ||
                 upperValue.includes('OTHER INCOME')) {
            this.cells[cellRef].style = 'header-section';
        }
        // Total/Summary styling
        else if (upperValue.includes('TOTAL') || 
                 upperValue.includes('GROSS') ||
                 upperValue.includes('NET') ||
                 upperValue.includes('CAPACITY')) {
            this.cells[cellRef].style = 'summary';
        }
    }

    // Print spreadsheet
    printSpreadsheet() {
        // Save current state
        this.saveData();
        
        // Trigger browser print dialog
        window.print();
    }

    // Select range of cells
    selectRange(startInput, endInput) {
        const startRow = parseInt(startInput.dataset.row, 10);
        const startCol = parseInt(startInput.dataset.col, 10);
        const endRow = parseInt(endInput.dataset.row, 10);
        const endCol = parseInt(endInput.dataset.col, 10);

        const minRow = Math.min(startRow, endRow);
        const maxRow = Math.max(startRow, endRow);
        const minCol = Math.min(startCol, endCol);
        const maxCol = Math.max(startCol, endCol);

        this.container.querySelectorAll('.cell-input').forEach((cell) => {
            cell.classList.remove('selected', 'range-selected');
        });
        this.clearSelectionChrome();

        this.selectedRange = [];
        for (let row = minRow; row <= maxRow; row++) {
            for (let col = minCol; col <= maxCol; col++) {
                const cellRef = this.getCellReference(row, col);
                const input = this.container.querySelector(`[data-cell="${cellRef}"]`);
                if (input) {
                    input.classList.add('range-selected');
                    this.selectedRange.push(cellRef);
                    const td = input.closest('td');
                    if (td) {
                        td.classList.add('excel-cell--range');
                    }
                }
            }
        }

        const brInput = this.container.querySelector(`[data-cell="${this.getCellReference(maxRow, maxCol)}"]`);
        if (brInput) {
            const brTd = brInput.closest('td');
            if (brTd) {
                brTd.classList.add('excel-cell--handle');
            }
        }

        // Update cell info
        const startRef = this.getCellReference(minRow, minCol);
        const endRef = this.getCellReference(maxRow, maxCol);
        const cellInfo = document.getElementById('cell-info');
        if (cellInfo) {
            cellInfo.textContent = `Range: ${startRef}:${endRef}`;
        }
    }

    // Merge selected cells
    mergeCells() {
        if (this.selectedRange.length < 2) {
            console.log('Please select multiple cells to merge (hold Shift and click)');
            // Show a subtle visual feedback instead of alert
            const notification = document.createElement('div');
            notification.className = 'excel-notification';
            notification.textContent = 'Select multiple cells to merge (click and drag)';
            notification.style.cssText = 'position: fixed; top: 80px; right: 20px; background: #495057; color: #fff; padding: 10px 20px; border-radius: 5px; z-index: 9999; box-shadow: 0 2px 10px rgba(0,0,0,0.2);';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 2000);
            return;
        }

        // Get range bounds
        const rows = this.selectedRange.map(ref => {
            const match = ref.match(/[A-Z]+(\d+)/);
            return parseInt(match[1]) - 1;
        });
        const cols = this.selectedRange.map(ref => {
            const match = ref.match(/([A-Z]+)\d+/);
            return this.getColumnIndex(match[1]);
        });

        const minRow = Math.min(...rows);
        const maxRow = Math.max(...rows);
        const minCol = Math.min(...cols);
        const maxCol = Math.max(...cols);

        const topLeftRef = this.getCellReference(minRow, minCol);
        const rowspan = maxRow - minRow + 1;
        const colspan = maxCol - minCol + 1;

        // Store merge info
        this.mergedCells[topLeftRef] = { rowspan, colspan };

        // Combine values from all cells
        let combinedValue = '';
        this.selectedRange.forEach(ref => {
            if (this.cells[ref] && this.cells[ref].value) {
                combinedValue += (combinedValue ? ' ' : '') + this.cells[ref].value;
            }
        });

        // Set combined value to top-left cell
        if (combinedValue) {
            this.setCellValue(topLeftRef, combinedValue);
        }

        // Re-render
        this.render();
        this.saveData();

        // Silent merge - no alert notification
        console.log(`Merged ${this.selectedRange.length} cells`);
    }

    // Unmerge selected cell
    unmergeCells() {
        if (!this.selectedCell) {
            console.log('Please select a merged cell to unmerge');
            // Show a subtle visual feedback instead of alert
            const notification = document.createElement('div');
            notification.className = 'excel-notification';
            notification.textContent = 'Select a merged cell to unmerge';
            notification.style.cssText = 'position: fixed; top: 80px; right: 20px; background: #495057; color: #fff; padding: 10px 20px; border-radius: 5px; z-index: 9999; box-shadow: 0 2px 10px rgba(0,0,0,0.2);';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 2000);
            return;
        }

        const cellRef = this.selectedCell.dataset.cell;
        
        if (this.mergedCells[cellRef]) {
            delete this.mergedCells[cellRef];
            this.render();
            this.saveData();
            // Silent unmerge - no alert notification
            console.log('Cells unmerged');
        } else {
            console.log('Selected cell is not merged');
            // Show a subtle visual feedback instead of alert
            const notification = document.createElement('div');
            notification.className = 'excel-notification';
            notification.textContent = 'Selected cell is not merged';
            notification.style.cssText = 'position: fixed; top: 80px; right: 20px; background: #17a2b8; color: #fff; padding: 10px 20px; border-radius: 5px; z-index: 9999; box-shadow: 0 2px 10px rgba(0,0,0,0.2);';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 2000);
        }
    }

    // Check if cell is hidden by a merge
    isCellHidden(cellRef) {
        const row = parseInt(cellRef.match(/\d+/)[0]) - 1;
        const col = this.getColumnIndex(cellRef.match(/[A-Z]+/)[0]);

        // Check all merged cells to see if this cell is within their range
        for (const [mergedRef, merge] of Object.entries(this.mergedCells)) {
            const mergedRow = parseInt(mergedRef.match(/\d+/)[0]) - 1;
            const mergedCol = this.getColumnIndex(mergedRef.match(/[A-Z]+/)[0]);

            const rowspan = merge.rowspan || 1;
            const colspan = merge.colspan || 1;

            // Check if current cell is within merged range (but not the top-left cell)
            if (row >= mergedRow && row < mergedRow + rowspan &&
                col >= mergedCol && col < mergedCol + colspan &&
                cellRef !== mergedRef) {
                return true;
            }
        }

        return false;
    }
}

// Initialize Excel spreadsheet
let excelSheet = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('excel-spreadsheet');
    if (container) {
        excelSheet = new ExcelSpreadsheet('excel-spreadsheet', 30, 15);
        window.excelSheet = excelSheet;
    }
});
