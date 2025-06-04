// Dashboard JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded');
    
    // Auto-refresh functionality
    let refreshInterval;
    
    function startAutoRefresh() {
        refreshInterval = setInterval(() => {
            location.reload();
        }, 10000); // Refresh every 10 seconds
    }
    
    function stopAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
        }
    }
    
    // Start auto-refresh by default
    startAutoRefresh();
    
    // Latency testing functionality
    const endpoints = [
        '/api/v1/health',
        '/api/v1/health/db',
        '/api/v1/health/cache',
        '/api/v1/users/count',
        '/api/v1/trips/total',
        '/api/v1/finance/revenue'
    ];
    
    async function testEndpoint(endpoint) {
        const startTime = performance.now();
        try {
            const response = await fetch(endpoint);
            const endTime = performance.now();
            const latency = Math.round(endTime - startTime);
            
            return {
                endpoint: endpoint,
                latency: latency,
                status: response.ok ? 'success' : 'error',
                statusCode: response.status
            };
        } catch (error) {
            const endTime = performance.now();
            const latency = Math.round(endTime - startTime);
            
            return {
                endpoint: endpoint,
                latency: latency,
                status: 'error',
                error: error.message
            };
        }
    }
    
    async function runLatencyTests() {
        const testButton = document.getElementById('test-latency');
        const resultsContainer = document.getElementById('latency-results');
        
        if (testButton) {
            testButton.disabled = true;
            testButton.textContent = 'Testing...';
        }
        
        if (resultsContainer) {
            resultsContainer.innerHTML = '<div>Running tests...</div>';
        }
        
        try {
            const promises = endpoints.map(endpoint => testEndpoint(endpoint));
            const results = await Promise.all(promises);
            
            if (resultsContainer) {
                resultsContainer.innerHTML = '';
                
                results.forEach(result => {
                    const item = document.createElement('div');
                    item.className = 'endpoint-item';
                    
                    let latencyClass = 'latency-fast';
                    if (result.latency > 100) latencyClass = 'latency-medium';
                    if (result.latency > 500) latencyClass = 'latency-slow';
                    
                    const statusIcon = result.status === 'success' ? '✅' : '❌';
                    
                    item.innerHTML = `
                        <span>${statusIcon} ${result.endpoint}</span>
                        <span class="${latencyClass}">${result.latency}ms</span>
                    `;
                    
                    resultsContainer.appendChild(item);
                });
            }
        } catch (error) {
            if (resultsContainer) {
                resultsContainer.innerHTML = `<div>Error running tests: ${error.message}</div>`;
            }
        }
        
        if (testButton) {
            testButton.disabled = false;
            testButton.textContent = 'Test Endpoint Latency';
        }
    }
    
    // Bind latency test button
    const testButton = document.getElementById('test-latency');
    if (testButton) {
        testButton.addEventListener('click', runLatencyTests);
    }
    
    // Add visibility change handler to pause/resume auto-refresh
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            stopAutoRefresh();
        } else {
            startAutoRefresh();
        }
    });
    
    console.log('Dashboard JavaScript initialized');
}); 