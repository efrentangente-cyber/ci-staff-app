// Excel-like Spreadsheet Component
// Full Excel functionality with formulas, cell references, and grid navigation

class ExcelSpreadsheet {
    constructor(containerId, rows = 50, cols = 26) {
        this.container = document.getElementById(containerId);
        this.rows = rows;
        this.cols = cols;
        this.cells = {}; // Store cell data: { 'A1': { value: '100', formula: '=B1*2', display: '200' } }
        this.selectedCell = null;
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
            <button class="btn btn-sm btn-primary" onclick="excelSheet.addRow()">
                <i class="bi bi-plus"></i> Add Row
            </button>
            <button class="btn btn-sm btn-primary" onclick="excelSheet.addColumn()">
                <i class="bi bi-plus"></i> Add Column
            </button>
            <button class="btn btn-sm btn-secondary" onclick="excelSheet.clearAll()">
                <i class="bi bi-trash"></i> Clear All
            </button>
            <button class="btn btn-sm btn-success" onclick="excelSheet.saveData()">
                <i class="bi bi-save"></i> Save
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

        // Column headers
        for (let col = 0; col < this.cols; col++) {
            const th = document.createElement('th');
            th.className = 'excel-col-header';
            th.textContent = this.getColumnName(col);
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
            rowTh.textContent = row + 1;
            tr.appendChild(rowTh);

            // Data cells
            for (let col = 0; col < this.cols; col++) {
                const td = document.createElement('td');
                td.className = 'excel-cell';
                
                const cellRef = this.getCellReference(row, col);
                td.dataset.cell = cellRef;
                td.dataset.row = row;
                td.dataset.col = col;

                // Create input
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'cell-input';
                input.dataset.cell = cellRef;

                // Load saved value
                if (this.cells[cellRef]) {
                    input.value = this.cells[cellRef].display || this.cells[cellRef].value || '';
                }

                td.appendChild(input);
                tr.appendChild(td);
            }
            tbody.appendChild(tr);
        }
        table.appendChild(tbody);
        gridDiv.appendChild(table);
        this.container.appendChild(gridDiv);
    }

    // Setup event listeners
    setupEventListeners() {
        // Cell click and input events
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('cell-input')) {
                this.selectCell(e.target);
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

        // Double-click to edit formula
        this.container.addEventListener('dblclick', (e) => {
            if (e.target.classList.contains('cell-input')) {
                const cellRef = e.target.dataset.cell;
                if (this.cells[cellRef] && this.cells[cellRef].formula) {
                    e.target.value = this.cells[cellRef].formula;
                    e.target.select();
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

        // Update formula bar
        const cellRef = input.dataset.cell;
        if (this.cells[cellRef]) {
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
        } else {
            // It's a plain value
            this.cells[cellRef].value = value;
            this.cells[cellRef].formula = null;
            this.cells[cellRef].display = value;
        }

        // Update formula bar
        this.formulaBar.value = value;

        // Recalculate dependent cells
        this.recalculateAll();

        // Auto-save
        this.saveData();
    }

    // Update cell from formula bar
    updateCellFromFormulaBar() {
        if (!this.selectedCell) return;

        const value = this.formulaBar.value;
        this.selectedCell.value = value;
        this.handleCellInput(this.selectedCell);
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
        this.saveData();
    }

    // Add column
    addColumn() {
        this.cols++;
        this.render();
        this.saveData();
    }

    // Clear all
    clearAll() {
        if (confirm('Clear all data? This cannot be undone.')) {
            this.cells = {};
            this.render();
            this.saveData();
        }
    }

    // Save data
    saveData() {
        const data = {
            rows: this.rows,
            cols: this.cols,
            cells: this.cells
        };
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
            cols: this.cols
        };
    }

    // Import from JSON
    importData(data) {
        this.cells = data.cells || {};
        this.rows = data.rows || this.rows;
        this.cols = data.cols || this.cols;
        this.render();
        this.recalculateAll();
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
