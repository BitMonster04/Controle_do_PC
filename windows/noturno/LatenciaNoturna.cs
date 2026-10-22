using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

// Atraso local por WinDivert. Nao registra conteudo de pacotes.
internal static class LatenciaNoturna
{
    [DllImport("WinDivert.dll", CallingConvention=CallingConvention.Cdecl, CharSet=CharSet.Ansi, SetLastError=true)]
    private static extern IntPtr WinDivertOpen(string filter, int layer, short priority, ulong flags);
    [DllImport("WinDivert.dll", CallingConvention=CallingConvention.Cdecl, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool WinDivertRecv(IntPtr h, [Out] byte[] packet, uint capacity, out uint length, [Out] byte[] address);
    [DllImport("WinDivert.dll", CallingConvention=CallingConvention.Cdecl, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool WinDivertSend(IntPtr h, byte[] packet, uint length, out uint sent, byte[] address);
    [DllImport("WinDivert.dll", CallingConvention=CallingConvention.Cdecl, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool WinDivertHelperCalcChecksums([In,Out] byte[] packet, uint length, [In,Out] byte[] address, ulong flags);
    [DllImport("WinDivert.dll", CallingConvention=CallingConvention.Cdecl, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool WinDivertShutdown(IntPtr h, int how);
    [DllImport("WinDivert.dll", CallingConvention=CallingConvention.Cdecl, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool WinDivertClose(IntPtr h);
    [DllImport("WinDivert.dll", CallingConvention=CallingConvention.Cdecl, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool WinDivertSetParam(IntPtr h, int param, ulong value);

    [DllImport("WinDivert.dll", CallingConvention=CallingConvention.Cdecl, CharSet=CharSet.Ansi, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool WinDivertHelperCompileFilter(string filter, int layer, IntPtr buffer, uint bufferLength, out IntPtr errorText, out uint errorPosition);

    private sealed class Packet { public byte[] Data, Address; public long Due; }
    private static readonly object Gate=new object();
    private static readonly Queue<Packet> Queue=new Queue<Packet>();
    private static readonly AutoResetEvent Signal=new AutoResetEvent(false);
    private static readonly Stopwatch Clock=new Stopwatch();
    private static readonly string Root=AppDomain.CurrentDomain.BaseDirectory;
    private static volatile bool Ending, ReceiverDone;
    private static string ReceiverError;
    private static long Bytes, LastDue, Count, Sent, Overflow;
    private static int ProbeMs;
    private static IntPtr Handle;

    internal static bool Night(DateTime now) { return now.Hour>=22 || now.Hour<6; }
    internal static int Delay(long ms) {
        long phase=ms%60000;
        return 150+(int)(550*(phase<=30000?phase:60000-phase)/30000);
    }
    private static void Log(string text) {
        try {
            string path=Path.Combine(Root,"noturno.log");
            if(File.Exists(path) && new FileInfo(path).Length>1048576) {
                string old=path+".1"; if(File.Exists(old))File.Delete(old); File.Move(path,old);
            }
            File.AppendAllText(path,DateTime.Now.ToString("o")+" "+text+Environment.NewLine);
        } catch { }
    }
    private static void Send(Packet packet) {
        uint sent;
        if(!WinDivertHelperCalcChecksums(packet.Data,(uint)packet.Data.Length,packet.Address,0) ||
           !WinDivertSend(Handle,packet.Data,(uint)packet.Data.Length,out sent,packet.Address)) {
            throw new InvalidOperationException("Falha ao reinjetar pacote; erro "+Marshal.GetLastWin32Error());
        }
        Interlocked.Increment(ref Sent);
    }
    private static void Receive() {
        byte[] buffer=new byte[65575];
        try {
            for(;;) {
                uint len; byte[] address=new byte[80];
                if(!WinDivertRecv(Handle,buffer,(uint)buffer.Length,out len,address)) {
                    int error=Marshal.GetLastWin32Error();
                    if(Ending && error==232)break;
                    throw new InvalidOperationException("Falha ao receber pacote; erro "+error);
                }
                byte[] data=new byte[len]; Buffer.BlockCopy(buffer,0,data,0,(int)len);
                var packet=new Packet {Data=data,Address=address};
                lock(Gate) {
                    // Ao atingir o limite, antecipa envio em vez de acumular memoria indefinidamente.
                    bool full=Bytes+len>16777216 || Queue.Count>=16384;
                    if(full) {
                        foreach(Packet queued in Queue)queued.Due=0;
                        LastDue=0; Overflow++;
                    }
                    packet.Due=Ending||full?0:Math.Max(LastDue,Clock.ElapsedMilliseconds+(ProbeMs>0?ProbeMs:Delay(Clock.ElapsedMilliseconds)));
                    LastDue=packet.Due; Queue.Enqueue(packet); Bytes+=len; Count++;
                }
                Signal.Set();
            }
        } catch(Exception e) { ReceiverError=e.Message; }
        finally {ReceiverDone=true;Signal.Set();}
    }
    private static bool SelfTest() {
        if(Night(new DateTime(2026,10,22,21,59,59)))return false;
        if(!Night(new DateTime(2026,10,22,22,0,0)))return false;
        if(!Night(new DateTime(2026,10,23,0,0,0)))return false;
        if(!Night(new DateTime(2026,10,23,5,59,59)))return false;
        if(Night(new DateTime(2026,10,23,6,0,0)))return false;
        if(Delay(0)!=150 || Delay(30000)!=700 || Delay(60000)!=150)return false;
        long previous=0;
        for(int t=0;t<180000;t++) {
            int d=Delay(t);if(d<150||d>700)return false;
            if(t+d<previous)return false;previous=t+d;
        }
        return true;
    }
    private static string Filter(int probe) {
        return probe>0?"outbound and icmp and ip.DstAddr == 1.1.1.1":
            "outbound and not loopback and (tcp or udp or icmp or icmpv6) "+
            "and (not tcp or (tcp.SrcPort != 22 and tcp.DstPort != 22 and tcp.DstPort != 443 and tcp.DstPort != 8443)) "+
            "and (not udp or (udp.SrcPort != 41641 and udp.DstPort != 41641 and udp.DstPort != 53 and udp.SrcPort != 53)) "+
            "and (not ip or ip.DstAddr < 100.64.0.0 or ip.DstAddr > 100.127.255.255) "+
            "and (not ip or ip.DstAddr < 10.0.0.0 or ip.DstAddr > 10.255.255.255) "+
            "and (not ip or ip.DstAddr < 172.16.0.0 or ip.DstAddr > 172.31.255.255) "+
            "and (not ip or ip.DstAddr < 192.168.0.0 or ip.DstAddr > 192.168.255.255) "+
            "and (not ipv6 or ipv6.DstAddr < fd00:: or ipv6.DstAddr > fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff)";
    }
    private static int Run(int probe) {
        ProbeMs=probe;
        if(probe==0 && File.Exists(Path.Combine(Root,"desativado.flag")))return 0;
        if(probe==0 && !Night(DateTime.Now)) {Log("Fora da janela 22h-06h; nenhum atraso aplicado.");return 0;}
        string stop=Path.Combine(Root,"parar.flag");
        if(probe==0 && File.Exists(stop))File.Delete(stop);
        string filter=Filter(probe);
        Handle=WinDivertOpen(filter,0,0,0);
        if(Handle==new IntPtr(-1))throw new InvalidOperationException("WinDivert recusou abertura; erro "+Marshal.GetLastWin32Error());
        WinDivertSetParam(Handle,0,8192); WinDivertSetParam(Handle,1,2000); WinDivertSetParam(Handle,2,16777216);
        var receiver=new Thread(Receive);receiver.IsBackground=true;
        Clock.Start(); receiver.Start();
        Log(probe>0?"Diagnostico ICMP 1.1.1.1: "+probe+" ms por 12 segundos.":"Trava noturna ativa: 150-700 ms, ciclo de 60 segundos.");
        try {
            long shutdownAt=0;
            for(;;) {
                if(!Ending && (ReceiverDone || (probe>0?Clock.ElapsedMilliseconds>=12000:
                    !Night(DateTime.Now)||File.Exists(stop)||File.Exists(Path.Combine(Root,"desativado.flag"))))) {
                    Ending=true;shutdownAt=Clock.ElapsedMilliseconds;
                    if(!WinDivertShutdown(Handle,1))throw new InvalidOperationException("Falha ao encerrar captura; erro "+Marshal.GetLastWin32Error());
                    Signal.Set();
                }
                if(Ending && !ReceiverDone && Clock.ElapsedMilliseconds-shutdownAt>3000)
                    throw new TimeoutException("Tempo limite ao encerrar captura; fechando driver.");
                Packet packet=null;int wait=100;
                lock(Gate) {
                    if(Queue.Count>0) {
                        Packet first=Queue.Peek();long remaining=first.Due-Clock.ElapsedMilliseconds;
                        if(Ending||remaining<=0) {packet=Queue.Dequeue();Bytes-=packet.Data.Length;}
                        else wait=(int)Math.Min(100,remaining);
                    } else if(Ending && ReceiverDone)break;
                }
                if(packet!=null)Send(packet);else Signal.WaitOne(Math.Max(1,wait));
            }
            if(ReceiverError!=null)throw new InvalidOperationException(ReceiverError);
            Log("Encerrado. Capturados="+Count+" enviados="+Sent+" antecipacoes_por_limite="+Overflow);
            return 0;
        } finally {
            Ending=true;WinDivertShutdown(Handle,1);receiver.Join(3000);
            try {lock(Gate){while(Queue.Count>0)Send(Queue.Dequeue());}}catch{}
            WinDivertClose(Handle);
        }
    }
    [STAThread]
    private static int Main(string[] args) {
        if(args.Length==1 && args[0]=="--self-test")return SelfTest()?0:2;
        if(args.Length==1 && args[0]=="--check-filter") {
            IntPtr error; uint position;
            bool ok=WinDivertHelperCompileFilter(Filter(0),0,IntPtr.Zero,0,out error,out position);
            Log(ok?"Filtro de producao validado.":"Filtro invalido na posicao "+position+": "+Marshal.PtrToStringAnsi(error));
            return ok?0:3;
        }
        int probe=0;
        if(args.Length>0) {
            if(args.Length!=2 || args[0]!="--probe-ms" || !int.TryParse(args[1],out probe) || (probe!=150&&probe!=700))return 2;
        }
        bool created;
        using(var mutex=new Mutex(true,"Global\\ControlePCGiovanni-LatenciaNoturna",out created)) {
            if(!created)return 0;
            try {return Run(probe);}catch(Exception e){Log("ERRO: "+e.Message);return 1;}
        }
    }
}
