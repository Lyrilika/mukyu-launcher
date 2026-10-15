#define NOMINMAX
#include <windows.h>
#include <roapi.h>
#include <systemmediatransportcontrolsinterop.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Media.h>
#include <winrt/Windows.Storage.h>
#include <winrt/Windows.Storage.Streams.h>
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <deque>
#include <memory>
#include <mutex>
#include <string>

using namespace winrt;
using namespace Windows::Foundation;
using namespace Windows::Media;
using namespace Windows::Storage;
using namespace Windows::Storage::Streams;

struct Session {
    SystemMediaTransportControls controls{nullptr};
    event_token buttons{}, position{}, shuffle{}, repeat{};
    bool has_buttons = false, has_position = false, has_shuffle = false, has_repeat = false;
    std::mutex mutex;
    std::deque<std::pair<int32_t, int64_t>> events;
    bool alive = true;
    uint64_t art_revision = 0;
    std::wstring artwork;
    std::wstring title, artist, album;
    RandomAccessStreamReference pending_art{nullptr};
    bool art_ready = false;
};

static std::shared_ptr<Session> current;
static bool initialized = false;

static void enqueue(std::weak_ptr<Session> weak, int32_t command, int64_t value = 0) noexcept {
    try {
        if (auto s = weak.lock()) {
            std::lock_guard<std::mutex> lock(s->mutex);
            if (!s->alive) return;
            if (s->events.size() == 32) s->events.pop_front();
            s->events.emplace_back(command, value);
        }
    } catch (...) {}
}

static fire_and_forget set_art(std::weak_ptr<Session> weak, std::wstring path, uint64_t revision) {
    try {
        co_await resume_background();
        RandomAccessStreamReference thumbnail{nullptr};
        if (path.rfind(L"https://", 0) == 0 || path.rfind(L"http://", 0) == 0) {
            thumbnail = RandomAccessStreamReference::CreateFromUri(Uri(path));
        } else if (!path.empty()) {
            auto file = co_await StorageFile::GetFileFromPathAsync(path);
            thumbnail = RandomAccessStreamReference::CreateFromFile(file);
        }
        if (auto s = weak.lock()) {
            std::lock_guard<std::mutex> lock(s->mutex);
            if (!s->alive || s->art_revision != revision) co_return;
            s->pending_art = thumbnail;
            s->art_ready = true;
        }
    } catch (...) {}
}

extern "C" __declspec(dllexport) void smtc_close() noexcept {
    auto s = std::move(current);
    if (s) {
        {
            std::lock_guard<std::mutex> lock(s->mutex);
            s->alive = false;
            s->events.clear();
            ++s->art_revision;
        }
        if (s->controls) {
            try { if (s->has_buttons) s->controls.ButtonPressed(s->buttons); } catch (...) {}
            try { if (s->has_position) s->controls.PlaybackPositionChangeRequested(s->position); } catch (...) {}
            try { if (s->has_shuffle) s->controls.ShuffleEnabledChangeRequested(s->shuffle); } catch (...) {}
            try { if (s->has_repeat) s->controls.AutoRepeatModeChangeRequested(s->repeat); } catch (...) {}
            try { s->controls.PlaybackStatus(MediaPlaybackStatus::Closed); s->controls.IsEnabled(false); } catch (...) {}
        }
        s.reset();
    }
    if (initialized) { RoUninitialize(); initialized = false; }
}

extern "C" __declspec(dllexport) int32_t smtc_create(HWND window) noexcept {
    smtc_close();
    try {
        HRESULT hr = RoInitialize(RO_INIT_SINGLETHREADED);
        if (FAILED(hr) && hr != RPC_E_CHANGED_MODE) return hr;
        initialized = SUCCEEDED(hr);
        auto s = std::make_shared<Session>();
        current = s;
        auto factory = get_activation_factory<SystemMediaTransportControls, ISystemMediaTransportControlsInterop>();
        check_hresult(factory->GetForWindow(window, guid_of<SystemMediaTransportControls>(), put_abi(s->controls)));
        std::weak_ptr<Session> weak = s;
        s->buttons = s->controls.ButtonPressed([weak](auto const&, SystemMediaTransportControlsButtonPressedEventArgs const& args) {
            switch (args.Button()) {
                case SystemMediaTransportControlsButton::Play: enqueue(weak, 1); break;
                case SystemMediaTransportControlsButton::Pause: enqueue(weak, 2); break;
                case SystemMediaTransportControlsButton::Stop: enqueue(weak, 3); break;
                case SystemMediaTransportControlsButton::Next: enqueue(weak, 4); break;
                case SystemMediaTransportControlsButton::Previous: enqueue(weak, 5); break;
                default: break;
            }
        });
        s->has_buttons = true;
        s->position = s->controls.PlaybackPositionChangeRequested([weak](auto const&, PlaybackPositionChangeRequestedEventArgs const& args) {
            enqueue(weak, 6, args.RequestedPlaybackPosition().count() / 10);
        });
        s->has_position = true;
        s->shuffle = s->controls.ShuffleEnabledChangeRequested([weak](auto const&, ShuffleEnabledChangeRequestedEventArgs const& args) {
            enqueue(weak, 7, args.RequestedShuffleEnabled());
        });
        s->has_shuffle = true;
        s->repeat = s->controls.AutoRepeatModeChangeRequested([weak](auto const&, AutoRepeatModeChangeRequestedEventArgs const& args) {
            enqueue(weak, 8, static_cast<int64_t>(args.RequestedAutoRepeatMode()));
        });
        s->has_repeat = true;
        s->controls.IsEnabled(false);
        s->controls.PlaybackRate(1.0);
        return S_OK;
    } catch (...) {
        auto hr = to_hresult();
        smtc_close();
        return hr;
    }
}

extern "C" __declspec(dllexport) int32_t smtc_update(
    wchar_t const* title, wchar_t const* artist, wchar_t const* album, wchar_t const* art,
    int32_t status, int32_t flags, int32_t repeat, int32_t shuffle) noexcept {
    try {
        auto s = current;
        if (!s) return E_UNEXPECTED;
        std::wstring artwork = art ? art : L"";
        uint64_t revision = 0;
        bool changed_art = false;
        {
            if (!s->alive) return E_UNEXPECTED;
            auto c = s->controls;
            c.IsEnabled((flags & 1) != 0);
            c.IsPlayEnabled((flags & 1) != 0);
            c.IsPauseEnabled((flags & 2) != 0);
            c.IsStopEnabled((flags & 1) != 0);
            c.IsNextEnabled((flags & 4) != 0);
            c.IsPreviousEnabled((flags & 8) != 0);
            c.PlaybackStatus(status == 2 ? MediaPlaybackStatus::Playing : status == 1 ? MediaPlaybackStatus::Paused : MediaPlaybackStatus::Stopped);
            c.AutoRepeatMode(static_cast<MediaPlaybackAutoRepeatMode>(repeat));
            c.ShuffleEnabled(shuffle != 0);
            std::wstring new_title = title ? title : L"", new_artist = artist ? artist : L"", new_album = album ? album : L"";
            changed_art = artwork != s->artwork;
            if (changed_art || new_title != s->title || new_artist != s->artist || new_album != s->album) {
                auto updater = c.DisplayUpdater();
                updater.Type(MediaPlaybackType::Music);
                auto music = updater.MusicProperties();
                music.Title(new_title); music.Artist(new_artist); music.AlbumTitle(new_album);
                if (changed_art) {
                    updater.Thumbnail(nullptr);
                    s->artwork = artwork;
                    std::lock_guard<std::mutex> lock(s->mutex);
                    revision = ++s->art_revision;
                    s->pending_art = nullptr;
                    s->art_ready = false;
                }
                updater.Update();
                s->title = new_title; s->artist = new_artist; s->album = new_album;
            }
        }
        if (changed_art) set_art(std::weak_ptr<Session>(s), artwork, revision);
        return S_OK;
    } catch (...) { return to_hresult(); }
}

extern "C" __declspec(dllexport) int32_t smtc_timeline(int64_t duration, int64_t position) noexcept {
    try {
        auto s = current;
        if (!s) return E_UNEXPECTED;
        duration = std::max<int64_t>(0, duration);
        position = std::clamp<int64_t>(position, 0, duration);
        SystemMediaTransportControlsTimelineProperties timeline;
        timeline.StartTime(TimeSpan{0}); timeline.MinSeekTime(TimeSpan{0});
        timeline.EndTime(TimeSpan{duration * 10}); timeline.MaxSeekTime(TimeSpan{duration * 10});
        timeline.Position(TimeSpan{position * 10});
        s->controls.UpdateTimelineProperties(timeline);
        return S_OK;
    } catch (...) { return to_hresult(); }
}

extern "C" __declspec(dllexport) int32_t smtc_poll(int32_t* command, int64_t* value) noexcept {
    try {
        auto s = current;
        if (!s || !command || !value) return 0;
        RandomAccessStreamReference thumbnail{nullptr};
        bool art_ready = false;
        int32_t found = 0;
        {
            std::lock_guard<std::mutex> lock(s->mutex);
            art_ready = s->art_ready;
            if (art_ready) {
                thumbnail = s->pending_art;
                s->pending_art = nullptr;
                s->art_ready = false;
            }
            if (!s->events.empty()) {
                *command = s->events.front().first; *value = s->events.front().second;
                s->events.pop_front();
                found = 1;
            }
        }
        if (art_ready) {
            auto updater = s->controls.DisplayUpdater();
            updater.Thumbnail(thumbnail);
            updater.Update();
        }
        return found;
    } catch (...) { return 0; }
}
