(function () {
    function createDashboard(options) {
        options = options || {};

        var timeoutMs = options.timeoutMs || 5000;
        var rpmValue = document.getElementById(options.rpmId || 'rpmValue');
        var boostValue = document.getElementById(options.boostId || 'boostValue');
        var iatValue = document.getElementById(options.iatId || 'iatValue');
        var onUpdate = typeof options.onUpdate === 'function' ? options.onUpdate : null;
        var timeoutHandle = null;

        function resetToPlaceholder() {
            if (rpmValue) rpmValue.textContent = '----';
            if (boostValue) boostValue.textContent = '--- psi';
            if (iatValue) iatValue.textContent = '---°';

            window.dashboardValues = {
                rpm: '----',
                boost: '--- psi',
                iat: '---°',
                raw: {
                    rpm: null,
                    boost: null,
                    iat: null
                }
            };
        }

        function scheduleReset() {
            clearTimeout(timeoutHandle);
            timeoutHandle = setTimeout(function () {
                resetToPlaceholder();
                if (typeof onUpdate === 'function') {
                    onUpdate(window.dashboardValues, null);
                }
            }, timeoutMs);
        }

        function updateRPM(rpm) {
            if (!rpmValue) return;

            if (rpm === "----" || rpm === undefined || rpm === null || rpm === "") {
                rpmValue.textContent = "----";
                scheduleReset();
                return "----";
            }

            var min = 0;
            var max = 8000;
            var clamped = Math.max(min, Math.min(max, Number(rpm)));
            var rpmText = String(Math.round(clamped));
            rpmValue.textContent = rpmText;
            scheduleReset();
            return rpmText;
        }

        function updateBoost(boost) {
            if (!boostValue) return;

            if (boost === "---" || boost === undefined || boost === null || boost === "") {
                boostValue.textContent = "--- psi";
                scheduleReset();
                return "--- psi";
            }

            var boostText = String(boost) + " psi";
            boostValue.textContent = boostText;
            scheduleReset();
            return boostText;
        }

        function updateIAT(iat) {
            if (!iatValue) return;

            if (iat === "---" || iat === undefined || iat === null || iat === "") {
                iatValue.textContent = "---°";
                scheduleReset();
                return "---°";
            }

            var iatText = String(iat) + "°";
            iatValue.textContent = iatText;
            scheduleReset();
            return iatText;
        }

        function emitUpdate(msg) {
            var rpmText = updateRPM(msg && msg.rpm);
            var boostText = updateBoost(msg && msg.boost_pressure);
            var iatText = updateIAT(msg && msg.intake_air_temp);

            var values = {
                rpm: rpmText,
                boost: boostText,
                iat: iatText,
                raw: {
                    rpm: msg && msg.rpm,
                    boost: msg && msg.boost_pressure,
                    iat: msg && msg.intake_air_temp
                }
            };

            window.dashboardValues = values;

            if (typeof onUpdate === 'function') {
                onUpdate(values, msg);
            }
        }

        function attachSocket() {
            if (!window.io) return null;

            var socket = io();

            socket.on('car_data', function (msg) {
                emitUpdate(msg);
            });

            return socket;
        }

        resetToPlaceholder();
        attachSocket();
        scheduleReset();

        return {
            updateRPM: updateRPM,
            updateBoost: updateBoost,
            updateIAT: updateIAT,
            emitUpdate: emitUpdate,
            resetToPlaceholder: resetToPlaceholder,
            values: window.dashboardValues
        };
    }

    window.BmwDashboard = createDashboard;
})();