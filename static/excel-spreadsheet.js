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
                input.placeholder = ''; // All cells are editable

                // Load saved value
                if (this.cells[cellRef]) {
                    input.value = this.cells[cellRef].display || this.cells[cellRef].value || '';
                    // Mark formula cells visually
                    if (this.cells[cellRef].formula) {
                        input.setAttribute('data-has-formula', 'true');
                        input.title = 'Double-click to edit formula: ' + this.cells[cellRef].formula;
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
        // Header
        this.setCellValue('A1', 'NENE SARI SARI STORE');
        this.setCellValue('A2', 'CASH FLOW STATEMENT');
        
        // SALES Section Header
        this.setCellValue('A4', 'SALES');
        this.setCellValue('B4', 'Qty/Month');
        this.setCellValue('C4', 'Unit Price');
        this.setCellValue('D4', 'Monthly Sales');
        
        // Product rows (labels only, values blank)
        const products = [
            'Softdrinks', 'Cigarettes', 'Candies', 'Biscuits', 'Noodles',
            'Coffee', 'Sugar', 'Rice', 'Cooking Oil', 'Soap'
        ];
        
        products.forEach((product, index) => {
            const row = 5 + index;
            this.setCellValue(`A${row}`, product);
            // B, C columns left blank for CI to fill
            // D column has formula
            this.setCellValue(`D${row}`, `=B${row}*C${row}`);
        });
        
        // Total Sales
        const totalRow = 5 + products.length;
        this.setCellValue(`A${totalRow}`, 'TOTAL SALES');
        this.setCellValue(`D${totalRow}`, `=SUM(D5:D${totalRow - 1})`);
        
        // Cost of Goods Sold (80%)
        const cogsRow = totalRow + 1;
        this.setCellValue(`A${cogsRow}`, 'COST OF GOODS SOLD (80%)');
        this.setCellValue(`D${cogsRow}`, `=D${totalRow}*0.8`);
        
        // Gross Sales
        const grossRow = cogsRow + 1;
        this.setCellValue(`A${grossRow}`, 'GROSS SALES');
        this.setCellValue(`D${grossRow}`, `=D${totalRow}-D${cogsRow}`);
        
        // OTHER BUSINESS Section
        const otherBusinessRow = grossRow + 2;
        this.setCellValue(`A${otherBusinessRow}`, 'OTHER BUSINESS');
        this.setCellValue(`A${otherBusinessRow + 1}`, 'Business Name:');
        this.setCellValue(`A${otherBusinessRow + 2}`, 'Monthly Income:');
        
        // OPERATING EXPENSES Section
        const expensesStartRow = otherBusinessRow + 4;
        this.setCellValue(`A${expensesStartRow}`, 'OPERATING EXPENSES');
        
        const expenses = [
            'Electric Bill', 'Water Bill', 'Fuel/Transportation',
            'House Rental', 'Food', 'Education', 'Miscellaneous'
        ];
        
        expenses.forEach((expense, index) => {
            const row = expensesStartRow + 1 + index;
            this.setCellValue(`A${row}`, expense);
            // Amount column left blank
        });
        
        // Total Operating Expenses
        const totalExpRow = expensesStartRow + 1 + expenses.length;
        this.setCellValue(`A${totalExpRow}`, 'TOTAL OPERATING EXPENSES');
        this.setCellValue(`D${totalExpRow}`, `=SUM(D${expensesStartRow + 1}:D${totalExpRow - 1})`);
        
        // Gross Profit
        const profitRow = totalExpRow + 1;
        this.setCellValue(`A${profitRow}`, 'GROSS PROFIT');
        this.setCellValue(`D${profitRow}`, `=D${grossRow}+D${otherBusinessRow + 2}-D${totalExpRow}`);
    }

    // Hollow Blocks / Sand & Gravel Template
    loadHollowBlocksTemplate() {
        // Header
        this.setCellValue('A1', 'SOURCES OF INCOME');
        this.setCellValue('B1', 'Weekly');
        this.setCellValue('C1', 'Monthly');
        
        // Income sources
        this.setCellValue('A3', 'Hollow Blocks Production');
        this.setCellValue('A4', 'Units Produced/Week:');
        this.setCellValue('A5', 'Price per Unit:');
        this.setCellValue('A6', 'Weekly Income:');
        this.setCellValue('B6', '=B4*B5');
        this.setCellValue('C6', '=B6*4');
        
        this.setCellValue('A8', 'Sand & Gravel Sales');
        this.setCellValue('A9', 'Trips/Week:');
        this.setCellValue('A10', 'Price per Trip:');
        this.setCellValue('A11', 'Weekly Income:');
        this.setCellValue('B11', '=B9*B10');
        this.setCellValue('C11', '=B11*4');
        
        this.setCellValue('A13', 'Other Income');
        this.setCellValue('A14', 'Source:');
        this.setCellValue('A15', 'Weekly Amount:');
        this.setCellValue('C15', '=B15*4');
        
        // Total Income
        this.setCellValue('A17', 'TOTAL MONTHLY INCOME');
        this.setCellValue('C17', '=C6+C11+C15');
        
        // OPERATING EXPENSES Section
        this.setCellValue('A19', 'OPERATING EXPENSES');
        this.setCellValue('B19', 'Weekly');
        this.setCellValue('C19', 'Monthly');
        
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
            const row = 20 + index;
            this.setCellValue(`A${row}`, expense);
            this.setCellValue(`C${row}`, `=B${row}*4`);
        });
        
        // Total Operating Expenses
        const totalExpRow = 20 + expenses.length;
        this.setCellValue(`A${totalExpRow}`, 'TOTAL OPERATING EXPENSES');
        this.setCellValue(`C${totalExpRow}`, `=SUM(C20:C${totalExpRow - 1})`);
        
        // Net Income
        const netRow = totalExpRow + 1;
        this.setCellValue(`A${netRow}`, 'NET MONTHLY INCOME');
        this.setCellValue(`C${netRow}`, `=C17-C${totalExpRow}`);
        
        // Debt Service Capacity
        const debtRow = netRow + 2;
        this.setCellValue(`A${debtRow}`, 'DEBT SERVICE CAPACITY (70%)');
        this.setCellValue(`C${debtRow}`, `=C${netRow}*0.7`);
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
