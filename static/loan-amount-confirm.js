/**
 * After the user leaves the loan amount field, show a one-time check per amount
 * until they confirm (avoids nagging on every blur for the same value).
 */
(function () {
    'use strict';

    function setupLoanAmountConfirmation(options) {
        var opts = options || {};
        var inputId = opts.inputId || 'loan_amount';
        var rawId = opts.rawId || 'loan_amount_raw';
        var noticeId = opts.noticeId || 'loanAmountConfirmNotice';

        var input = document.getElementById(inputId);
        var raw = document.getElementById(rawId);
        var box = document.getElementById(noticeId);
        if (!input || !raw || !box) {
            return;
        }
        if (input.readOnly || input.disabled) {
            return;
        }

        var suppressedFor = '';

        function hide() {
            box.hidden = true;
            box.classList.add('d-none');
        }

        function show(num) {
            var el = box.querySelector('[data-loan-confirm-amount]');
            if (el) {
                el.textContent =
                    '₱' +
                    Number(num).toLocaleString(undefined, {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 2,
                    });
            }
            box.hidden = false;
            box.classList.remove('d-none');
        }

        input.addEventListener('input', function () {
            if (String(raw.value).trim() !== suppressedFor) {
                suppressedFor = '';
            }
            hide();
        });

        input.addEventListener('blur', function () {
            var v = String(raw.value || '').trim();
            var n = parseFloat(v);
            if (!v || !isFinite(n) || n <= 0) {
                hide();
                return;
            }
            if (suppressedFor === v) {
                return;
            }
            show(n);
        });

        var dismiss = box.querySelector('[data-loan-confirm-dismiss]');
        if (dismiss) {
            dismiss.addEventListener('click', function () {
                suppressedFor = String(raw.value || '').trim();
                hide();
            });
        }
    }

    window.setupLoanAmountConfirmation = setupLoanAmountConfirmation;

    document.addEventListener('DOMContentLoaded', function () {
        if (document.getElementById('loanAmountConfirmNotice')) {
            setupLoanAmountConfirmation({});
        }
    });
})();
