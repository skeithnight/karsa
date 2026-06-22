/**
 * NotificationCenter -- Phase-7
 * Toast notifications for important events
 */

'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
}

interface NotificationContextType {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markRead: (id: string) => void;
  clearAll: () => void;
  unreadCount: number;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
}

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback(
    (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
      const newNotification: Notification = {
        ...notification,
        id: `notif-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp: new Date(),
        read: false,
      };
      setNotifications(prev => [newNotification, ...prev].slice(0, 50)); // keep last 50
    },
    []
  );

  const markRead = useCallback((id: string) => {
    setNotifications(prev =>
      prev.map(n => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <NotificationContext.Provider
      value={{ notifications, addNotification, markRead, clearAll, unreadCount }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

/** Toast notification that auto-dismisses */
export function ToastNotification({
  notification,
  onDismiss,
}: {
  notification: Notification;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const typeStyles = {
    success: 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950',
    error: 'border-red-500 bg-red-50 dark:bg-red-950',
    warning: 'border-amber-500 bg-amber-50 dark:bg-amber-950',
    info: 'border-blue-500 bg-blue-50 dark:bg-blue-950',
  };

  return (
    <div
      className={`border-l-4 p-4 rounded shadow-lg ${typeStyles[notification.type]} max-w-sm`}
      role="alert"
    >
      <div className="flex justify-between items-start">
        <div>
          <div className="font-semibold text-sm">{notification.title}</div>
          <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            {notification.message}
          </div>
        </div>
        <button
          onClick={onDismiss}
          className="text-slate-400 hover:text-slate-600 ml-2"
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
    </div>
  );
}

/** Toast container that shows active notifications */
export function ToastContainer() {
  const { notifications, markRead } = useNotifications();
  const unread = notifications.filter(n => !n.read);

  if (unread.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {unread.slice(0, 3).map(notification => (
        <ToastNotification
          key={notification.id}
          notification={notification}
          onDismiss={() => markRead(notification.id)}
        />
      ))}
    </div>
  );
}
