// Cash Flow Calculator - Excel-like Spreadsheet with Auto-calculations
// Supports multiple templates and custom template creation

class CashFlowCalculator {
    constructor() {
        this.currentTemplate = null;
        this.cashFlowData = {};
        this.init();
    }

    init() {
        // Load saved data if exists
        this.loadSavedData();
    }

    // Pre-defined templates
    getTemplates() {
        return {
            'sari_sari_store': {
                name: 'Sari-Sari Store',
                sections: [
                    {
                        title: 'SALES',
                        type: 'income',
                        rows: [
                            { label: 'Product Name', qty: 'Qty/Month', price: 'Unit Price', total: 'Monthly Sales' }
                        ],
                        defaultRows: 10,
                        showCostOfGoods: true,
                        costPercentage: 80
                    },
                    {
                        title: 'OTHER BUSINESS',
                        type: 'income',
                        rows: [
                            { label: 'Source', qty: '', price: '', total: 'Amount' }
                        ],
                        defaultRows: 3
                    },
                    {
                        title: 'OPERATING EXPENSES',
                        type: 'expense',
                        rows: [
                            { label: 'Expense Item', amount: 'Monthly Amount' }
                        ],
                        defaultRows: 10
                    }
                ]
            },
            'hollow_blocks': {
                name: 'Hollow Blocks, Sand & Gravel',
                sections: [
                    {
                        title: 'SOURCES OF INCOME',
                        type: 'income',
                        rows: [
                            { label: 'Product/Service', qty: 'Qty/Week', price: 'Unit Price', weekly: 'Weekly Sales', total: 'Monthly Income' }
                        ],
                        defaultRows: 5
                    },
                    {
                        title: 'OPERATING EXPENSES (Monthly)',
                        type: 'expense',
                        rows: [
                            { label: 'Expense Item', amount: 'Monthly Amount' }
                        ],
                        defaultRows: 10
                    }
                ]
            },
            'custom': {
                name: 'Custom Template',
                sections: []
            }
        };
    }

    // Load template
    loadTemplate(templateKey) {
        this.currentTemplate = templateKey;
        const templates = this.getTemplates();
        const template = templates[templateKey];
        
        if (!template) return;

        const container = document.getElementById('cashflow-container');
        container.innerHTML = '';

        // Add template header
        const header = document.createElement('div');
        header.className = 'cashflow-header';
        header.innerHTML = `
            <h4>${template.name}</h4>
            <small>Fill in all fields - calculations are automatic</small>
        `;
        container.appendChild(header);

        // Render sections
        template.sections.forEach((section, sectionIndex) => {
            this.renderSection(container, section, sectionIndex);
        });

        // Add totals section
        this.renderTotals(container);

        // Add custom template builder button if custom
        if (templateKey === 'custom') {
            this.renderCustomBuilder(container);
        }
    }

    // Render section
    renderSection(container, section, sectionIndex) {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'cashflow-section';
        sectionDiv.dataset.sectionIndex = sectionIndex;
        sectionDiv.dataset.sectionType = section.type;

        // Section title
        const title = document.createElement('div');
        title.className = 'section-title';
        title.textContent = section.title;
        sectionDiv.appendChild(title);

        // Create table
        const table = document.createElement('table');
        table.className = 'cashflow-table';

        // Table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        const headerTemplate = section.rows[0];
        Object.keys(headerTemplate).forEach(key => {
            const th = document.createElement('th');
            th.textContent = headerTemplate[key];
            headerRow.appendChild(th);
        });
        
        // Add action column
        const actionTh = document.createElement('th');
        actionTh.textContent = 'Action';
        actionTh.style.width = '80px';
        headerRow.appendChild(actionTh);
        
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Table body
        const tbody = document.createElement('tbody');
        tbody.dataset.sectionIndex = sectionIndex;
        
        // Add default rows
        const rowCount = section.defaultRows || 5;
        for (let i = 0; i < rowCount; i++) {
            this.addRow(tbody, section, sectionIndex, i);
        }
        
        table.appendChild(tbody);
        sectionDiv.appendChild(table);

        // Add row button
        const addButton = document.createElement('button');
        addButton.type = 'button';
        addButton.className = 'btn btn-sm btn-outline-primary mt-2';
        addButton.innerHTML = '<i class="bi bi-plus"></i> Add Row';
        addButton.onclick = () => {
            const rowIndex = tbody.children.length;
            this.addRow(tbody, section, sectionIndex, rowIndex);
        };
        sectionDiv.appendChild(addButton);

        // Show cost of goods if applicable
        if (section.showCostOfGoods) {
            const costDiv = document.createElement('div');
            costDiv.className = 'cost-summary mt-3';
            costDiv.innerHTML = `
                <table class="form-table-paper">
                    <tr>
                        <td><strong>TOTAL SALES:</strong></td>
                        <td><input type="number" id="total_sales_${sectionIndex}" readonly class="form-control" value="0"></td>
                    </tr>
                    <tr>
                        <td><strong>COST OF GOODS SOLD (${section.costPercentage}%):</strong></td>
                        <td><input type="number" id="cost_of_goods_${sectionIndex}" readonly class="form-control" value="0"></td>
                    </tr>
                    <tr style="background: #f0f0f0;">
                        <td><strong>GROSS SALES:</strong></td>
                        <td><input type="number" id="gross_sales_${sectionIndex}" readonly class="form-control" value="0" style="font-weight: bold;"></td>
                    </tr>
                </table>
            `;
            sectionDiv.appendChild(costDiv);
        }

        container.appendChild(sectionDiv);
    }

    // Add row to table
    addRow(tbody, section, sectionIndex, rowIndex) {
        const tr = document.createElement('tr');
        tr.dataset.rowIndex = rowIndex;

        const headerTemplate = section.rows[0];
        const keys = Object.keys(headerTemplate);

        keys.forEach((key, colIndex) => {
            const td = document.createElement('td');
            const input = document.createElement('input');
            input.type = key === 'label' ? 'text' : 'number';
            input.step = '0.01';
            input.className = 'form-control form-control-sm';
            input.name = `cf_s${sectionIndex}_r${rowIndex}_${key}`;
            input.placeholder = key === 'label' ? 'Enter name' : '0';
            
            if (key !== 'label' && key !== 'total' && key !== 'weekly') {
                input.value = '0';
            }

            // Auto-calculate on input
            if (key === 'qty' || key === 'price') {
                input.oninput = () => this.calculateRow(tr, section, sectionIndex);
            }

            // Readonly for calculated fields
            if (key === 'total' || key === 'weekly') {
                input.readOnly = true;
                input.style.background = '#f0f0f0';
                input.value = '0';
            }

            td.appendChild(input);
            tr.appendChild(td);
        });

        // Add delete button
        const actionTd = document.createElement('td');
        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'btn btn-sm btn-outline-secondary';
        deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
        deleteBtn.onclick = () => {
            tr.remove();
            this.calculateSection(sectionIndex);
        };
        actionTd.appendChild(deleteBtn);
        tr.appendChild(actionTd);

        tbody.appendChild(tr);
    }

    // Calculate row totals
    calculateRow(tr, section, sectionIndex) {
        const inputs = tr.querySelectorAll('input[type="number"]');
        let qty = 0, price = 0;

        inputs.forEach(input => {
            const name = input.name;
            if (name.includes('_qty')) qty = parseFloat(input.value) || 0;
            if (name.includes('_price')) price = parseFloat(input.value) || 0;
        });

        // Calculate total
        const total = qty * price;

        // Update total field
        inputs.forEach(input => {
            if (input.name.includes('_total')) {
                input.value = total.toFixed(2);
            }
            if (input.name.includes('_weekly')) {
                input.value = (total * 4).toFixed(2); // Weekly to monthly
            }
        });

        // Recalculate section
        this.calculateSection(sectionIndex);
    }

    // Calculate section totals
    calculateSection(sectionIndex) {
        const section = document.querySelector(`[data-section-index="${sectionIndex}"]`);
        if (!section) return;

        const tbody = section.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        
        let sectionTotal = 0;

        rows.forEach(row => {
            const totalInput = row.querySelector('input[name*="_total"]');
            if (totalInput) {
                sectionTotal += parseFloat(totalInput.value) || 0;
            }
        });

        // Update cost of goods if applicable
        const totalSalesInput = document.getElementById(`total_sales_${sectionIndex}`);
        if (totalSalesInput) {
            totalSalesInput.value = sectionTotal.toFixed(2);
            
            const costInput = document.getElementById(`cost_of_goods_${sectionIndex}`);
            const grossInput = document.getElementById(`gross_sales_${sectionIndex}`);
            
            const costPercentage = 80; // Default 80%
            const costOfGoods = sectionTotal * (costPercentage / 100);
            const grossSales = sectionTotal - costOfGoods;
            
            costInput.value = costOfGoods.toFixed(2);
            grossInput.value = grossSales.toFixed(2);
        }

        // Recalculate grand totals
        this.calculateGrandTotals();
    }

    // Render totals section
    renderTotals(container) {
        const totalsDiv = document.createElement('div');
        totalsDiv.className = 'cashflow-totals mt-4';
        totalsDiv.innerHTML = `
            <table class="form-table-paper">
                <tr style="background: #d4edda;">
                    <td><strong>TOTAL MONTHLY INCOME:</strong></td>
                    <td><input type="number" id="total_monthly_income" readonly class="form-control" value="0" style="font-weight: bold; font-size: 16px;"></td>
                </tr>
                <tr style="background: #f8d7da;">
                    <td><strong>TOTAL OPERATING EXPENSES:</strong></td>
                    <td><input type="number" id="total_operating_expenses" readonly class="form-control" value="0" style="font-weight: bold; font-size: 16px;"></td>
                </tr>
                <tr style="background: #fff3cd;">
                    <td><strong>GROSS PROFIT (Income - Expenses):</strong></td>
                    <td><input type="number" id="gross_profit" readonly class="form-control" value="0" style="font-weight: bold; font-size: 18px;"></td>
                </tr>
            </table>
        `;
        container.appendChild(totalsDiv);
    }

    // Calculate grand totals
    calculateGrandTotals() {
        let totalIncome = 0;
        let totalExpenses = 0;

        // Sum all income sections
        document.querySelectorAll('[data-section-type="income"]').forEach(section => {
            const sectionIndex = section.dataset.sectionIndex;
            const tbody = section.querySelector('tbody');
            const rows = tbody.querySelectorAll('tr');
            
            rows.forEach(row => {
                const totalInput = row.querySelector('input[name*="_total"]');
                if (totalInput) {
                    totalIncome += parseFloat(totalInput.value) || 0;
                }
            });

            // Add gross sales if applicable
            const grossSalesInput = document.getElementById(`gross_sales_${sectionIndex}`);
            if (grossSalesInput) {
                totalIncome = parseFloat(grossSalesInput.value) || 0;
            }
        });

        // Sum all expense sections
        document.querySelectorAll('[data-section-type="expense"]').forEach(section => {
            const tbody = section.querySelector('tbody');
            const rows = tbody.querySelectorAll('tr');
            
            rows.forEach(row => {
                const amountInput = row.querySelector('input[name*="_amount"]');
                if (amountInput) {
                    totalExpenses += parseFloat(amountInput.value) || 0;
                }
            });
        });

        // Update grand totals
        document.getElementById('total_monthly_income').value = totalIncome.toFixed(2);
        document.getElementById('total_operating_expenses').value = totalExpenses.toFixed(2);
        document.getElementById('gross_profit').value = (totalIncome - totalExpenses).toFixed(2);

        // Save data
        this.saveData();
    }

    // Render custom template builder
    renderCustomBuilder(container) {
        const builderDiv = document.createElement('div');
        builderDiv.className = 'custom-builder mt-4';
        builderDiv.innerHTML = `
            <div class="alert alert-info">
                <h5><i class="bi bi-tools"></i> Custom Template Builder</h5>
                <p>Add your own income sources and expense categories:</p>
                <button type="button" class="btn btn-primary btn-sm" onclick="cashFlowCalc.addCustomSection('income')">
                    <i class="bi bi-plus"></i> Add Income Section
                </button>
                <button type="button" class="btn btn-warning btn-sm" onclick="cashFlowCalc.addCustomSection('expense')">
                    <i class="bi bi-plus"></i> Add Expense Section
                </button>
            </div>
        `;
        container.appendChild(builderDiv);
    }

    // Add custom section
    addCustomSection(type) {
        const sectionName = prompt(`Enter ${type} section name:`);
        if (!sectionName) return;

        const container = document.getElementById('cashflow-container');
        const sectionIndex = document.querySelectorAll('.cashflow-section').length;

        const section = {
            title: sectionName,
            type: type,
            rows: type === 'income' 
                ? [{ label: 'Source', qty: 'Quantity', price: 'Price', total: 'Total' }]
                : [{ label: 'Expense Item', amount: 'Amount' }],
            defaultRows: 5
        };

        this.renderSection(container, section, sectionIndex);
    }

    // Save data
    saveData() {
        const data = {
            template: this.currentTemplate,
            totalIncome: document.getElementById('total_monthly_income')?.value || 0,
            totalExpenses: document.getElementById('total_operating_expenses')?.value || 0,
            grossProfit: document.getElementById('gross_profit')?.value || 0,
            sections: []
        };

        // Save all section data
        document.querySelectorAll('.cashflow-section').forEach(section => {
            const sectionData = {
                title: section.querySelector('.section-title').textContent,
                type: section.dataset.sectionType,
                rows: []
            };

            const tbody = section.querySelector('tbody');
            tbody.querySelectorAll('tr').forEach(row => {
                const rowData = {};
                row.querySelectorAll('input').forEach(input => {
                    rowData[input.name] = input.value;
                });
                sectionData.rows.push(rowData);
            });

            data.sections.push(sectionData);
        });

        this.cashFlowData = data;
        sessionStorage.setItem('cashflow_data', JSON.stringify(data));

        // Auto-fill Page 3 income field
        this.autoFillPage3();
    }

    // Load saved data
    loadSavedData() {
        const saved = sessionStorage.getItem('cashflow_data');
        if (saved) {
            this.cashFlowData = JSON.parse(saved);
        }
    }

    // Auto-fill Page 3 with cash flow data
    autoFillPage3() {
        const totalIncome = parseFloat(this.cashFlowData.totalIncome) || 0;
        const totalExpenses = parseFloat(this.cashFlowData.totalExpenses) || 0;
        const grossProfit = parseFloat(this.cashFlowData.grossProfit) || 0;

        // Fill "Income from Business" field in Page 3
        const incomeBusinessField = document.querySelector('[name="income_business"]');
        if (incomeBusinessField && grossProfit > 0) {
            incomeBusinessField.value = grossProfit.toFixed(2);
            
            // Trigger computation update
            if (typeof updateAllComputations === 'function') {
                updateAllComputations();
            }

            // Show notification
            this.showNotification('Cash Flow data auto-filled to Page 3!');
        }
    }

    // Show notification
    showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'alert alert-success alert-dismissible fade show';
        notification.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            <i class="bi bi-check-circle"></i> ${message}
        `;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }
}

// Initialize calculator
const cashFlowCalc = new CashFlowCalculator();
window.cashFlowCalc = cashFlowCalc;
