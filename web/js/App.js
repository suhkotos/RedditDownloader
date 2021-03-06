class App extends React.Component {
	constructor(props) {
		super(props);
		let hash = window.location.hash.substr(1);
		let current = 0;
		this._openPage = this.openPage.bind(this);
		this._start_download = this.startDownload.bind(this);
		this._get_progress = this.getProgress.bind(this);
		this.pages = [
			[<Home getProgress={this._get_progress}/>, 'Home', true],
			[<Sources />, 'Sources', false],
			[<Settings />, 'Settings', false],
			[<Browser />, 'Browser', true]
		];
		for(let i=0; i < this.pages.length; i++)
			if(this.pages[i][1].toLowerCase() === hash.toLowerCase())
				current = i;
		this.state = {page: current, downloading: false, progress: null};
		this.check_timer = null;
		this.checkStatus()
	}

	checkStatus() {
		async function run() {
			// Inside a function marked 'async' we can use the 'await' keyword.
			return await eel.download_status()(); // Must prefix call with 'await'
		}
		let warning = setTimeout(()=>{
			alertify.alert('<b>RMD has been disconnected!</b>' +
				'<br>The backend may not be running, or is not reachable with current configuration.' +
				'<br>Settings you change now will not be savable.' +
				'<br><br>Please refresh this window once RMD has been restarted.').then(()=>{location.reload()})
		}, 5000);

		run().then((r)=>{
			let page = this.state.page;
			let name = this.pages[page][1];
			console.log('RMD running status: ', r);
			if(r.running && this.pages[page][2] === false){
				page = 0;
				alertify.log('The '+name+' panel is disabled while RMD is downloading!')
			}
			this.setState({
				downloading: r.running,
				page: page
			});
			clearTimeout(warning);
			this.check_timer = setTimeout(this.checkStatus.bind(this), 1500)
		})
	}

	openPage(page){
		console.log('Switching tab:', page);
		window.location.hash = this.pages[page][1];
		this.setState({
			page: page
		});
	}

	startDownload(evt){
		evt.preventDefault();
		if(this.state.downloading)
			return;
		console.log('Starting RMD download process!');
		eel.start_download()(n => {
			if (n) {
				clearTimeout(this.check_timer);
				this.checkStatus();
			} else {
				alertify.error('Unable to start RMD downloading - Is it already running?')
			}
		});
	}

	getProgress(){
		return this.state.progress;
	}

	render() {
		let pages = this.pages.map((p)=>{
			let idx = this.pages.indexOf(p);
			if(this.state.downloading && this.pages[idx][2] === false){
				return <li className={'inactive disabled'} key={idx}><a>{p[1]}</a></li>
			} else {
				return <li className={this.state.page === idx ? 'active' : 'inactive'} key={idx}>
					<a onClick={this._openPage.bind(this, idx)}>{p[1]}</a>
				</li>
			}
		});
		let eles = this.pages.map((p)=>{
			let idx = this.pages.indexOf(p);
			return <div key={idx} className={this.state.page === idx? 'active_page_container':'hidden'} >{p[0]}</div>
		});
		let run_btn = <li className={'right ' + (this.state.downloading ? 'disabled' : 'special')} key={'dl_button'}>
			<a onClick={this._start_download}>{this.state.downloading?'Downloading...':'Start Downloading!'}</a>
		</li>;

		return (
			<div>
				<ul className="header">
					{pages}{run_btn}
				</ul>
				<div className="content">
					{eles}
				</div>
			</div>
		);
	}
}

ReactDOM.render(
	<App />,
	document.getElementById('root')
);