(function () {
    function createDashboard(options) {
        options = options || {};

        var timeoutMs = options.timeoutMs || 5000;
        var rpmValue = document.getElementById(options.rpmId || 'rpmValue');
        var boostValue = document.getElementById(options.boostId || 'boostValue');
        var iatValue = document.getElementById(options.iatId || 'iatValue');
        var coolantTempValue = document.getElementById(options.coolantTempId || 'coolantTempValue');
        var coolantTempRadOutValue = document.getElementById(options.coolantTempRadOutId || 'coolantTempRadOutValue');
        var oilTempValue = document.getElementById(options.oilTempId || 'oilTempValue');

        var onUpdate = typeof options.onUpdate === 'function' ? options.onUpdate : null;
        var timeoutHandle = null;

        function resetToPlaceholder() {
            if (rpmValue) rpmValue.textContent = '----';
            if (boostValue) boostValue.textContent = '--- psi';
            if (iatValue) iatValue.textContent = '---°';
            if (coolantTempValue) coolantTempValue.textContent = '---°';
            if (coolantTempRadOutValue) coolantTempRadOutValue.textContent = '---°';
            if (oilTempValue) oilTempValue.textContent = '---°';

            window.dashboardValues = {
                rpm: '----',
                boost: '--- psi',
                iat: '---°',
                coolantTemp: '---°',
                coolantTempRadOut: '---°',
                oilTemp: '---°',
                raw: {
                    rpm: null,
                    boost: null,
                    iat: null,
                    coolantTemp: null,
                    coolantTempRadOut: null,
                    oilTemp: null
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
            var max = 7000;
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

        function updateCoolantTemp(coolant_temp) {
            if (!coolantTempValue) return;

            if (coolant_temp === "---" || coolant_temp === undefined || coolant_temp === null || coolant_temp === "") {
                coolantTempValue.textContent = "---°";
                scheduleReset();
                return "---°";
            }

            var coolantTempText = String(coolant_temp) + "°";
            coolantTempValue.textContent = coolantTempText;
            scheduleReset();
            return coolantTempText;
        }

        function updateCoolantTempRadOut(coolant_temp_rad_out) {
            if (!coolantTempRadOutValue) return;
            
            if (coolant_temp_rad_out === "---" || coolant_temp_rad_out === undefined || coolant_temp_rad_out === null || coolant_temp_rad_out === "") {
                coolantTempRadOutValue.textContent = "---°";
                scheduleReset();
                return "---°";
            }

            var coolantTempRadOutText = String(coolant_temp_rad_out) + "°";
            coolantTempRadOutValue.textContent = coolantTempRadOutText;
            scheduleReset();
            return coolantTempRadOutText;
        }

        function updateOilTemp(oil_temp) {
            if (!oilTempValue) return;
            
            if (oil_temp === "---" || oil_temp === undefined || oil_temp === null || oil_temp === "") {
                oilTempValue.textContent = "---°";
                scheduleReset();
                return "---°";
            }

            var oilTempText = String(oil_temp) + "°";
            oilTempValue.textContent = oilTempText;
            scheduleReset();
            return oilTempText;
        }

        function emitUpdate(msg) {
            var rpmText = updateRPM(msg && msg.rpm);
            var boostText = updateBoost(msg && msg.boost_pressure);
            var iatText = updateIAT(msg && msg.intake_air_temp);
            var coolantTempText = updateCoolantTemp(msg && msg.coolant_temp);
            var coolantTempRadOutText = updateCoolantTempRadOut(msg && msg.coolant_temp_rad_out);
            var oilTempText = updateOilTemp(msg && msg.oil_temp);

            var values = {
                rpm: rpmText,
                boost: boostText,
                iat: iatText,
                coolant_temp: coolantTempText,
                coolant_temp_rad_out: coolantTempRadOutText,
                oil_temp: oilTempText,
                raw: {
                    rpm: msg && msg.rpm,
                    boost: msg && msg.boost_pressure,
                    iat: msg && msg.intake_air_temp,
                    coolant_temp: msg && msg.coolant_temp,
                    coolant_temp_rad_out: msg && msg.coolant_temp_rad_out,
                    oil_temp: msg && msg.oil_temp
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
            updateCoolantTemp: updateCoolantTemp,
            updateOilTemp: updateOilTemp,
            emitUpdate: emitUpdate,
            resetToPlaceholder: resetToPlaceholder,
            values: window.dashboardValues
        };
    }

    window.BmwDashboard = createDashboard;
})();