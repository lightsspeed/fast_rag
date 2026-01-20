import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { ChevronDown } from 'lucide-react';
import { 
  Gauge, FileText, Wifi, KeyRound, Package, Cpu, Monitor, 
  Printer, Shield, Radio, Smartphone
} from 'lucide-react';

interface ITSupportNavbarProps {
  onSelectIssue: (query: string) => void;
}

const categories = [
  {
    id: 'performance',
    icon: Gauge,
    label: 'Performance',
    issues: [
      { 
        label: 'System running slow', 
        query: 'My computer is running extremely slow. Applications take forever to open, and the system becomes unresponsive frequently. I need help diagnosing and fixing the performance issues.' 
      },
      { 
        label: 'High CPU/Memory usage', 
        query: 'Task Manager shows very high CPU or memory usage even when I am not running heavy applications. The system fans are constantly running and performance is degraded.' 
      },
      { 
        label: 'Startup taking too long', 
        query: 'My computer takes an unusually long time to boot up and become usable. The login screen appears slowly and desktop takes minutes to fully load.' 
      },
    ]
  },
  {
    id: 'msoffice',
    icon: FileText,
    label: 'MS Office Issues',
    issues: [
      { 
        label: 'Outlook not opening / crashing', 
        query: 'Microsoft Outlook is not opening or keeps crashing immediately after launch. I have tried restarting my computer but the issue persists. I need to access my emails urgently.' 
      },
      { 
        label: 'Word/Excel/PowerPoint issues', 
        query: 'Microsoft Office applications (Word, Excel, or PowerPoint) are not working properly. Files are not opening, applications are crashing, or features are not functioning correctly.' 
      },
      { 
        label: 'Office activation errors', 
        query: 'I am getting Microsoft Office activation errors. The applications show unlicensed product warnings or ask me to activate even though I have a valid license.' 
      },
      { 
        label: 'Mailbox full Issues', 
        query: 'I am receiving notifications that my mailbox is full and I cannot send or receive new emails. I need help archiving old emails or increasing my mailbox quota.' 
      },
      { 
        label: 'OST/PST Access/Issues', 
        query: 'I am having problems accessing my Outlook data files (OST/PST). The files may be corrupted or I am getting errors when trying to open my archived emails.' 
      },
      { 
        label: 'Mailbox Sync issues', 
        query: 'My Outlook mailbox is not syncing properly with the server. New emails are not appearing, or sent emails are stuck in the outbox. Calendar items are also not updating.' 
      },
    ]
  },
  {
    id: 'network',
    icon: Wifi,
    label: 'Network & VPN',
    issues: [
      { 
        label: 'Internet not connecting', 
        query: 'My computer is not connecting to the internet. The network icon shows no connection or limited connectivity. I have tried restarting but still cannot access any websites.' 
      },
      { 
        label: 'Zscaler Issues', 
        query: 'I am experiencing issues with Zscaler. The client is not connecting, showing authentication errors, or blocking legitimate websites and applications that I need for work.' 
      },
      { 
        label: 'Wi-Fi drops frequently', 
        query: 'My Wi-Fi connection keeps dropping intermittently. I get disconnected randomly throughout the day and have to reconnect manually. This is affecting my productivity.' 
      },
      { 
        label: 'Cannot access internal apps', 
        query: 'I am unable to access internal company applications or intranet sites. The pages timeout or show connection errors even though my internet is working for external sites.' 
      },
    ]
  },
  {
    id: 'password',
    icon: KeyRound,
    label: 'Password & Account',
    issues: [
      { 
        label: 'Password reset request', 
        query: 'I need to reset my password. Either I have forgotten my current password, it has expired, or I am locked out due to too many failed attempts.' 
      },
      { 
        label: 'MFA issues', 
        query: 'I am having problems with Multi-Factor Authentication (MFA). The authenticator app is not working, I am not receiving codes, or I need to re-register my MFA device.' 
      },
      { 
        label: 'Account locked', 
        query: 'My account has been locked and I cannot log in to my computer or access company resources. I need urgent assistance to unlock my account.' 
      },
    ]
  },
  {
    id: 'software',
    icon: Package,
    label: 'Software & Access',
    issues: [
      { 
        label: 'Additional Software Requests', 
        query: 'I need additional software installed on my computer for work purposes. Please help me request and install the required application following company policies.' 
      },
      { 
        label: 'Software not installing', 
        query: 'I am trying to install approved software but the installation keeps failing. I am getting error messages or the installer crashes during the process.' 
      },
      { 
        label: 'License errors', 
        query: 'I am receiving license activation errors for my software. The application says my license is expired, invalid, or has reached maximum activations.' 
      },
      { 
        label: 'Version incompatibility', 
        query: 'I am facing compatibility issues with software versions. An application is not working correctly due to version conflicts or requires an update/downgrade.' 
      },
      { 
        label: 'Permission denied', 
        query: 'I am getting "Access Denied" or permission errors when trying to install or run software. I may need elevated privileges or access rights to proceed.' 
      },
    ]
  },
  {
    id: 'hardware',
    icon: Cpu,
    label: 'Hardware',
    issues: [
      { 
        label: 'Laptop not powering on', 
        query: 'My laptop is not turning on at all. The power button does not respond, or there are no lights or sounds when I try to start it.' 
      },
      { 
        label: 'Battery drain issues', 
        query: 'My laptop battery is draining very quickly even with minimal usage. The battery percentage drops rapidly or the laptop shuts down unexpectedly.' 
      },
      { 
        label: 'Keyboard / mouse issues', 
        query: 'My keyboard or mouse is not working properly. Keys are not responding, the mouse cursor is stuck, or the devices are not being recognized by the computer.' 
      },
      { 
        label: 'Overheating problems', 
        query: 'My computer is overheating. The fans are running constantly at high speed, the device feels very hot, and performance is throttling due to heat.' 
      },
    ]
  },
  {
    id: 'os',
    icon: Monitor,
    label: 'OS Errors',
    issues: [
      { 
        label: 'Blue Screen (BSOD)', 
        query: 'I am getting Blue Screen of Death (BSOD) errors. My computer crashes with a blue screen showing error codes, and I need help diagnosing and fixing this issue.' 
      },
      { 
        label: 'Windows update failures', 
        query: 'Windows updates are failing to install. I am getting error codes during updates, or updates get stuck at a certain percentage and never complete.' 
      },
      { 
        label: 'Boot issues', 
        query: 'My computer is not booting properly. It gets stuck on the loading screen, shows boot errors, or goes into a repair loop without reaching the desktop.' 
      },
      { 
        label: 'General OS Issues', 
        query: 'I am experiencing general Windows operating system issues. System features are not working correctly, settings are not saving, or there are stability problems.' 
      },
    ]
  },
  {
    id: 'printer',
    icon: Printer,
    label: 'Printer Issues',
    issues: [
      { 
        label: 'Printer Installation', 
        query: 'I need help installing a new printer on my computer. I have the printer connected but it is not appearing in my devices or I cannot complete the setup.' 
      },
      { 
        label: 'Printer not printing', 
        query: 'My printer is not printing. Print jobs are stuck in the queue, nothing comes out, or the printer shows as offline even though it is turned on and connected.' 
      },
      { 
        label: 'Driver issues', 
        query: 'I am having printer driver issues. The driver needs to be updated, reinstalled, or there are compatibility problems with my current Windows version.' 
      },
      { 
        label: 'Network printer mapping', 
        query: 'I need help mapping a network printer to my computer. I cannot find the shared printer or I am getting access denied errors when trying to connect.' 
      },
    ]
  },
  {
    id: 'security',
    icon: Shield,
    label: 'Security Alerts',
    issues: [
      { 
        label: 'Zscaler blocking websites', 
        query: 'Zscaler is blocking a website or application that I need for legitimate work purposes. I need to request access or get an exception for this specific site.' 
      },
      { 
        label: 'BitLocker recovery', 
        query: 'I am being prompted for a BitLocker recovery key and cannot access my computer. I need help retrieving my recovery key or resolving the BitLocker prompt.' 
      },
    ]
  },
  {
    id: 'remote',
    icon: Radio,
    label: 'Remote Access',
    issues: [
      { 
        label: 'TeamViewer not connecting', 
        query: 'TeamViewer is not connecting to the remote computer. I am getting connection timeout errors or the remote session fails to establish.' 
      },
      { 
        label: 'User offline issues', 
        query: 'The remote user appears offline in our remote support tools. I cannot establish a connection to provide assistance. Help troubleshoot the connectivity issue.' 
      },
    ]
  },
  {
    id: 'mobile',
    icon: Smartphone,
    label: 'Mobile Apps',
    issues: [
      { 
        label: 'Company app not installing', 
        query: 'I am unable to install the company mobile app on my device. The installation fails or the app is not available in my app store.' 
      },
      { 
        label: 'Mobile email setup', 
        query: 'I need help setting up my work email on my mobile device. The configuration is not working or I am getting authentication errors.' 
      },
      { 
        label: 'MDM enrollment issues', 
        query: 'I am having problems enrolling my device in Mobile Device Management (MDM). The enrollment process fails or my device is not being recognized.' 
      },
      { 
        label: 'App sync problems', 
        query: 'Company apps on my mobile device are not syncing data properly. Information is outdated or changes are not being saved to the server.' 
      },
    ]
  },
];

export function ITSupportNavbar({ onSelectIssue }: ITSupportNavbarProps) {
  return (
    <nav className="flex items-center gap-1">
      {categories.map((category) => (
        <DropdownMenu key={category.id}>
          <DropdownMenuTrigger asChild>
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground hover:bg-accent/50"
            >
              <category.icon className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">{category.label}</span>
              <ChevronDown className="w-3 h-3 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent 
            align="start" 
            className="w-[280px] max-h-[400px] overflow-y-auto bg-popover z-50"
          >
            {category.issues.map((issue, idx) => (
              <DropdownMenuItem 
                key={idx}
                onClick={() => onSelectIssue(issue.query)}
                className="cursor-pointer py-2.5"
              >
                <span className="text-sm">{issue.label}</span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      ))}
    </nav>
  );
}
