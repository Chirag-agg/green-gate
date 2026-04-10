/**
 * Structured frontend logger with module tagging.
 */

const emit = (level, module, event, data = {}) => {
    const payload = {
        timestamp: new Date().toISOString(),
        level,
        module,
        event,
        data,
    };

    if (level === 'error') {
        console.error(payload);
        return;
    }
    if (level === 'warn') {
        console.warn(payload);
        return;
    }
    console.info(payload);
};

export const createLogger = (module) => ({
    info: (event, data) => emit('info', module, event, data),
    warn: (event, data) => emit('warn', module, event, data),
    error: (event, data) => emit('error', module, event, data),
});
