document.addEventListener("DOMContentLoaded", function () {

    const data = window.profileData;
    const canvas = document.getElementById("activityChart");

    if (!data || !canvas || !data.dates.length) return;

    const ctx = canvas.getContext("2d");

    // Gradient fill under line
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, "rgba(52, 152, 219, 0.4)");
    gradient.addColorStop(1, "rgba(52, 152, 219, 0.05)");

    new Chart(ctx, {
        type: "line",
        data: {
            labels: data.dates,
            datasets: [{
                label: "Work Hours",
                data: data.hours,
                fill: true,
                backgroundColor: gradient,
                borderColor: "#3498db",
                borderWidth: 3,
                tension: 0.4,           // smooth curve
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 900
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            return value + "h";
                        }
                    },
                    title: {
                        display: true,
                        text: "Hours"
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {

                            const decimalHours = context.raw;
                            const totalMinutes = Math.floor(decimalHours * 60);
                            const hours = Math.floor(totalMinutes / 60);
                            const minutes = totalMinutes % 60;

                            return hours + "h " + minutes + "m";
                        }
                    }
                },
                legend: {
                    display: false
                }
            }
        }
    });

});