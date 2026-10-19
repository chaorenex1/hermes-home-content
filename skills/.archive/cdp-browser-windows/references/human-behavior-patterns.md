# Human Behavior Simulation Patterns for CDP

## Mouse Movement (Bezier Curve)

Simulates natural human hand movement with slight randomness:

```javascript
async function humanMouseMove(ws, x1, y1, x2, y2) {
    const steps = 15 + Math.floor(Math.random() * 10);
    for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        // Add sine wave jitter for natural curve
        const x = x1 + (x2 - x1) * t + Math.sin(t * Math.PI) * (Math.random() * 20 - 10);
        const y = y1 + (y2 - y1) * t + Math.sin(t * Math.PI) * (Math.random() * 20 - 10);
        await cdpSend(ws, 'Input.dispatchMouseEvent', {
            type: 'mouseMoved',
            x: Math.round(x),
            y: Math.round(y)
        });
        await sleep(20 + Math.random() * 30); // 20-50ms between steps
    }
}
```

## Click Simulation

```javascript
async function humanClick(ws, x, y) {
    // Move to target with natural path
    await humanMouseMove(ws, 
        100 + Math.random() * 200,  // Start from random position
        100 + Math.random() * 200,
        x, y
    );
    
    // Pause before click (human reaction time)
    await sleep(100 + Math.random() * 200);
    
    // Mouse down
    await cdpSend(ws, 'Input.dispatchMouseEvent', {
        type: 'mousePressed',
        x: Math.round(x),
        y: Math.round(y),
        button: 'left',
        clickCount: 1
    });
    
    // Brief hold
    await sleep(50 + Math.random() * 100);
    
    // Mouse up
    await cdpSend(ws, 'Input.dispatchMouseEvent', {
        type: 'mouseReleased',
        x: Math.round(x),
        y: Math.round(y),
        button: 'left',
        clickCount: 1
    });
}
```

## Natural Scrolling

```javascript
async function humanScroll(ws, deltaY) {
    const steps = Math.abs(deltaY) / 50;
    for (let i = 0; i < steps; i++) {
        await cdpSend(ws, 'Input.dispatchMouseEvent', {
            type: 'mouseWheel',
            x: 500 + Math.random() * 200, // Random position on page
            y: 500 + Math.random() * 200,
            deltaX: 0,
            deltaY: deltaY > 0 ? 50 : -50
        });
        // Variable delay between scroll events
        await sleep(100 + Math.random() * 200);
    }
}
```

## Random Delays

```javascript
// Wait for JS rendering (3-6 seconds)
await sleep(3000 + Math.random() * 3000);

// Pause between actions (0.5-1.5 seconds)
await sleep(500 + Math.random() * 1000);

// Longer pause for reading (2-4 seconds)
await sleep(2000 + Math.random() * 2000);
```

## Viewport and User Agent

```javascript
// Set realistic desktop viewport
await cdpSend(ws, 'Emulation.setDeviceMetricsOverride', {
    width: 1920,
    height: 1080,
    deviceScaleFactor: 1,
    mobile: false
});

// Use real browser user agent
await cdpSend(ws, 'Emulation.setUserAgentOverride', {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0'
});

// Disable touch emulation (desktop behavior)
await cdpSend(ws, 'Emulation.setTouchEmulationEnabled', { enabled: false });
```

## Complete Human Session Example

```javascript
async function simulateHumanSession(ws) {
    // 1. Initial page load wait
    await sleep(3000 + Math.random() * 3000);
    
    // 2. Move mouse to center of page
    await humanMouseMove(ws, 200, 200, 960, 540);
    await sleep(500 + Math.random() * 1000);
    
    // 3. Scroll down to see content
    await humanScroll(ws, 500);
    await sleep(1000 + Math.random() * 2000);
    
    // 4. Scroll back up slightly
    await humanScroll(ws, -300);
    await sleep(500 + Math.random() * 1000);
    
    // 5. Move to a potential clickable area
    await humanMouseMove(ws, 960, 540, 600, 300);
    await sleep(300 + Math.random() * 500);
    
    // 6. Maybe click (70% chance)
    if (Math.random() < 0.7) {
        await humanClick(ws, 600, 300);
        await sleep(2000 + Math.random() * 3000);
    }
}
```

## Anti-Detection Tips

1. **Variable timing**: Never use fixed delays
2. **Bezier curves**: Linear mouse movement is detectable
3. **Viewport consistency**: Match the user's actual screen resolution
4. **Real user agent**: Use the browser's actual UA string
5. **Scroll patterns**: Humans scroll in chunks, not continuously
6. **Mouse pauses**: Humans pause to read, not just scroll through

---

*Last updated: 2026-06-29*
