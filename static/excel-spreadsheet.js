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
            <button class="btn btn-sm btn-primary" onclick="excelSheet.addRow()" title="Add Row">
                <i class="bi bi-plus"></i> Add Row
            </button>
            <button class="btn btn-sm btn-primary" onclick="excelSheet.addColumn()" title="Add Column">
                <i class="bi bi-plus"></i> Add Column
            </button>
            <div class="toolbar-divider"></div>
            <button class="btn btn-sm btn-secondary" onclick="excelSheet.alignText('left')" title="Align Left">
                <i class="bi bi-text-left"></i>
            </button>
            <button class="btn btn-sm btn-secondary" onclick="excelSheet.alignText('center')" title="Align Center">
                <i class="bi bi-text-center"></i>
            </button>
            <button class="btn btn-sm btn-secondary" onclick="excelSheet.alignText('right')" title="Align Right">
                <i class="bi bi-text-right"></i>
            </button>
            <div class="toolbar-divider"></div>
            <button class="btn btn-sm btn-warning" onclick="excelSheet.mergeCells()" title="Merge Cells">
                <i class="bi bi-border-outer"></i> Merge
            </button>
            <button class="btn btn-sm btn-warning" onclick="excelSheet.unmergeCells()" title="Unmerge Cells">
                <i class="bi bi-border-inner"></i> Unmerge
            </button>
            <div class="toolbar-divider"></div>
            <button class="btn btn-sm btn-danger" onclick="excelSheet.clearAll()" title="Clear All">
                <i class="bi bi-trash"></i> Clear
            </button>
            <button class="btn btn-sm btn-success" onclick="excelSheet.saveData()" title="Save">
                <i class="bi bi-save"></i> Save
            </button>
            <button class="btn btn-sm btn-info" onclick="excelSheet.printSpreadsheet()" title="Print">
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
            <input type="text" id="formula-input" class="formula-input" placeholder="Enter value or formula (e.g., =A1+B1)">
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
                    // Always show the display value (calculated result), never the formula
                    input.value = this.cells[cellRef].display || this.cells[cellRef].value || '';
                    
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

    // Setup event listeners
    setupEventListeners() {
        // Mouse down - start selection
        this.container.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('cell-input')) {
                this.isSelecting = true;
                this.selectionStart = e.target;
                this.selectCell(e.target);
                this.container.classList.add('is-selecting');
                e.preventDefault(); // Prevent text selection
            }
        });

        // Mouse move - extend selection
        this.container.addEventListener('mousemove', (e) => {
            if (this.isSelecting && e.target.classList.contains('cell-input')) {
                this.selectRange(this.selectionStart, e.target);
            }
        });

        // Mouse up - end selection
        this.container.addEventListener('mouseup', (e) => {
            if (this.isSelecting) {
                this.isSelecting = false;
                this.container.classList.remove('is-selecting');
            }
        });

        // Mouse leave - end selection if dragging outside
        this.container.addEventListener('mouseleave', (e) => {
            if (this.isSelecting) {
                this.isSelecting = false;
                this.container.classList.remove('is-selecting');
            }
        });

        this.container.addEventListener('input', (e) => {
            if (e.target.classList.contains('cell-input')) {
                this.handleCellInput(e.target);
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

    // Select cell
    selectCell(input) {
        // Remove previous selection
        document.querySelectorAll('.cell-input').forEach(cell => {
            cell.classList.remove('selected');
        });

        // Add selection
        input.classList.add('selected');
        this.selectedCell = input;

        // Update formula bar - show formula if exists, otherwise show value
        const cellRef = input.dataset.cell;
        if (this.cells[cellRef]) {
            // Show formula in formula bar (if it has one)
            this.formulaBar.value = this.cells[cellRef].formula || this.cells[cellRef].value || '';
        } else {
            this.formulaBar.value = input.value;
        }

        // Update cell info
        document.getElementById('cell-info').textContent = `Cell: ${cellRef}`;
    }

    // Handle cell input
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
            input.value = this.cells[cellRef].display || '#ERROR!';
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

        // Recalculate dependent cells
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

            // Replace cell references with values
            formula = this.replaceCellReferences(formula);

            // Evaluate formula
            const result = this.evaluateExpression(formula);
            cell.display = result;

            // Update display
            const input = document.querySelector(`[data-cell="${cellRef}"]`);
            if (input) {
                input.value = result;
            }
        } catch (error) {
            cell.display = '#ERROR!';
            const input = document.querySelector(`[data-cell="${cellRef}"]`);
            if (input) {
                input.value = '#ERROR!';
            }
        }
    }

    // Replace cell references in formula
    replaceCellReferences(formula) {
        // Match cell references like A1, B2, etc.
        const cellRefPattern = /([A-Z]+)(\d+)/g;
        
        return formula.replace(cellRefPattern, (match, col, row) => {
            const cellRef = col + row;
            const cell = this.cells[cellRef];
            
            if (cell) {
                // Use display value if available, otherwise value
                const value = cell.display || cell.value || '0';
                // Remove any non-numeric characters except decimal point and minus
                const numericValue = value.toString().replace(/[^\d.-]/g, '');
                return numericValue || '0';
            }
            return '0';
        });
    }

    // Evaluate expression (supports basic math and functions)
    evaluateExpression(expression) {
        // Handle SUM function
        expression = this.handleSumFunction(expression);
        
        // Handle AVERAGE function
        expression = this.handleAverageFunction(expression);

        // Handle other functions as needed
        
        try {
            // Use Function constructor for safe evaluation
            const result = new Function('return ' + expression)();
            return this.formatNumber(result);
        } catch (error) {
            return '#ERROR!';
        }
    }

    // Handle SUM function
    handleSumFunction(expression) {
        const sumPattern = /SUM\(([A-Z]+\d+):([A-Z]+\d+)\)/gi;
        
        return expression.replace(sumPattern, (match, start, end) => {
            const values = this.getCellRange(start, end);
            const sum = values.reduce((acc, val) => acc + (parseFloat(val) || 0), 0);
            return sum;
        });
    }

    // Handle AVERAGE function
    handleAverageFunction(expression) {
        const avgPattern = /AVERAGE\(([A-Z]+\d+):([A-Z]+\d+)\)/gi;
        
        return expression.replace(avgPattern, (match, start, end) => {
            const values = this.getCellRange(start, end);
            const sum = values.reduce((acc, val) => acc + (parseFloat(val) || 0), 0);
            const avg = sum / values.length;
            return avg;
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

    // Recalculate all formulas
    recalculateAll() {
        Object.keys(this.cells).forEach(cellRef => {
            if (this.cells[cellRef].formula) {
                this.evaluateFormula(cellRef);
            }
        });
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
                e.preventDefault();
                newRow = Math.max(0, row - 1);
                break;
            case 'ArrowDown':
            case 'Enter':
                e.preventDefault();
                newRow = Math.min(this.rows - 1, row + 1);
                break;
            case 'ArrowLeft':
                if (e.target.selectionStart === 0) {
                    e.preventDefault();
                    newCol = Math.max(0, col - 1);
                }
                break;
            case 'ArrowRight':
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

    // Get cell reference (e.g., A1, B2)
    getCellReference(row, col) {
        return this.getColumnName(col) + (row + 1);
    }

    // Format number
    formatNumber(num) {
        if (isNaN(num)) return num;
        // Format with 2 decimal places if needed
        return Number(num).toFixed(2).replace(/\.?0+$/, '');
    }

    // Add row
    addRow() {
        this.rows++;
        this.render();
        this.recalculateAll();
        this.saveData();
    }

    // Add column
    addColumn() {
        this.cols++;
        this.render();
        this.recalculateAll();
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
            alert('Please select a cell or range to align');
            return;
        }
        
        this.saveData();
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
        const startRow = parseInt(startInput.dataset.row);
        const startCol = parseInt(startInput.dataset.col);
        const endRow = parseInt(endInput.dataset.row);
        const endCol = parseInt(endInput.dataset.col);

        const minRow = Math.min(startRow, endRow);
        const maxRow = Math.max(startRow, endRow);
        const minCol = Math.min(startCol, endCol);
        const maxCol = Math.max(startCol, endCol);

        // Clear previous selection
        document.querySelectorAll('.cell-input').forEach(cell => {
            cell.classList.remove('selected', 'range-selected');
        });

        // Select range
        this.selectedRange = [];
        for (let row = minRow; row <= maxRow; row++) {
            for (let col = minCol; col <= maxCol; col++) {
                const cellRef = this.getCellReference(row, col);
                const input = document.querySelector(`[data-cell="${cellRef}"]`);
                if (input) {
                    input.classList.add('range-selected');
                    this.selectedRange.push(cellRef);
                }
            }
        }

        // Update cell info
        const startRef = this.getCellReference(minRow, minCol);
        const endRef = this.getCellReference(maxRow, maxCol);
        document.getElementById('cell-info').textContent = `Range: ${startRef}:${endRef}`;
    }

    // Merge selected cells
    mergeCells() {
        if (this.selectedRange.length < 2) {
            alert('Please select multiple cells to merge (hold Shift and click)');
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
            alert('Please select a merged cell to unmerge');
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
            alert('Selected cell is not merged');
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
